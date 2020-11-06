#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
End-to-end testing for the chat demo crowdsourcing task.
"""

import unittest

try:

    # From the Mephisto repo
    # TODO: revise below
    from examples.parlai_chat_task_demo.parlai_test_script import TASK_DIRECTORY
    from mephisto.server.blueprints.parlai_chat.parlai_chat_blueprint import (
        SharedParlAITaskState,
        BLUEPRINT_TYPE,
    )

    from parlai.crowdsourcing.utils.tests import CrowdsourcingTestMixin

    class TestChatDemo(CrowdsourcingTestMixin, unittest.TestCase):
        """
        Test the chat demo crowdsourcing task.
        """

        def test_base_task(self):

            # # Setup

            # Set up the config and database
            overrides = [
                '+mephisto.blueprint.world_file=${task_dir}/demo_worlds.py',
                '+mephisto.blueprint.task_description_file=${task_dir}/task_description.html',
                '+mephisto.blueprint.num_conversations=1',
                '+mephisto.task.allowed_concurrent=0',
                '+num_turns=3',
                '+turn_timeout=300',
            ]
            # TODO: remove all of these params once Hydra 1.1 is released with support
            #  for recursive defaults
            self._set_up_config(
                blueprint_type=BLUEPRINT_TYPE,
                task_directory=TASK_DIRECTORY,
                overrides=overrides,
            )

            # Set up the operator and server
            world_opt = {
                "num_turns": self.config.num_turns,
                "turn_timeout": self.config.turn_timeout,
            }
            shared_state = SharedParlAITaskState(
                world_opt=world_opt, onboarding_world_opt=world_opt
            )
            self._set_up_server(shared_state=shared_state)

            # Set up the mock human agents
            agent_0_id, agent_1_id = self._register_mock_agents(num_agents=2)

            # # Feed messages to the agents

            # Set initial data
            self.server.request_init_data(agent_0_id)
            self.server.request_init_data(agent_1_id)

            # Have agents talk to each other
            for agent_0_text, agent_1_text in AGENT_MESSAGES:
                self._send_agent_message(
                    agent_id=agent_0_id,
                    agent_display_id=AGENT_0_DISPLAY_ID,
                    text=agent_0_text,
                )
                self._send_agent_message(
                    agent_id=agent_1_id,
                    agent_display_id=AGENT_1_DISPLAY_ID,
                    text=agent_1_text,
                )

            # Have agents fill out the form
            self.server.send_agent_act(
                agent_id=agent_0_id,
                act_content={
                    'text': FORM_PROMPTS['agent_0'],
                    'task_data': {'form_responses': FORM_RESPONSES['agent_0']},
                    'id': AGENT_0_DISPLAY_ID,
                    'episode_done': False,
                },
            )
            self.server.send_agent_act(
                agent_id=agent_1_id,
                act_content={
                    'text': FORM_PROMPTS['agent_1'],
                    'task_data': {'form_responses': FORM_RESPONSES['agent_1']},
                    'id': AGENT_1_DISPLAY_ID,
                    'episode_done': False,
                },
            )

            # Submit the HIT
            self.server.send_agent_act(
                agent_id=agent_0_id,
                act_content={
                    'task_data': {'final_data': {}},
                    'MEPHISTO_is_submit': True,
                },
            )
            self.server.send_agent_act(
                agent_id=agent_1_id,
                act_content={
                    'task_data': {'final_data': {}},
                    'MEPHISTO_is_submit': True,
                },
            )

            # # Check that the inputs and outputs are as expected

            state_0, state_1 = [
                agent.state.get_data() for agent in self.db.find_agents()
            ]
            actual_and_desired_states = [
                (state_0, DESIRED_STATE_AGENT_0),
                (state_1, DESIRED_STATE_AGENT_1),
            ]
            for actual_state, desired_state in actual_and_desired_states:
                assert actual_state['inputs'] == desired_state['inputs']
                assert len(actual_state['outputs']['messages']) == len(
                    desired_state['outputs']['messages']
                )
                for actual_message, desired_message in zip(
                    actual_state['outputs']['messages'],
                    desired_state['outputs']['messages'],
                ):
                    for key, desired_value in desired_message.items():
                        if key == 'timestamp':
                            pass  # The timestamp will obviously be different
                        elif key == 'data':
                            for key_inner, desired_value_inner in desired_message[
                                key
                            ].items():
                                if key_inner == 'message_id':
                                    pass  # The message ID will be different
                                else:
                                    self.assertEqual(
                                        actual_message[key][key_inner],
                                        desired_value_inner,
                                    )
                        else:
                            self.assertEqual(actual_message[key], desired_value)

        def _send_agent_message(self, agent_id: str, agent_display_id: str, text: str):
            """
            Have the agent specified by agent_id send the specified text with the given
            display ID string.
            """
            act_content = {
                "text": text,
                "task_data": {},
                "id": agent_display_id,
                "episode_done": False,
            }
            self.server.send_agent_act(agent_id=agent_id, act_content=act_content)


except ImportError:
    pass

if __name__ == "__main__":
    unittest.main()