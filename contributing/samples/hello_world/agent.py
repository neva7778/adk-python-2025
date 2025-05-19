# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random

from google.adk import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.planners import PlanReActPlanner
from google.adk.tools.tool_context import ToolContext
from google.genai import types


def roll_die(sides: int, tool_context: ToolContext) -> int:
  """Roll a die and return the rolled result.

  Args:
    sides: The integer number of sides the die has.

  Returns:
    An integer of the result of rolling the die.
  """
  result = random.randint(1, sides)
  if not 'rolls' in tool_context.state:
    tool_context.state['rolls'] = []

  tool_context.state['rolls'] = tool_context.state['rolls'] + [result]
  print(f"[ HERRAMIENTA roll_die ] Llamada con sides={sides}. Devolviendo: {result}")
  return result


async def check_prime(nums: list[int]) -> str:
  """Check if a given list of numbers are prime.

  Args:
    nums: The list of numbers to check.

  Returns:
    A str indicating which number is prime.
  """
  primes = set()
  for number in nums:
    number = int(number)
    if number <= 1:
      continue
    is_prime = True
    for i in range(2, int(number**0.5) + 1):
      if number % i == 0:
        is_prime = False
        break
    if is_prime:
      primes.add(number)
  resultado_string = (
    'No prime numbers found.'
    if not primes
    else f"{', '.join(str(num) for num in primes)} are prime numbers."
)
  print(f"[ HERRAMIENTA check_prime ] Llamada con nums={nums}. Devolviendo: \"{resultado_string}\"")
  return resultado_string


root_agent = Agent(
    model='gemini-2.0-flash',
    name='data_processing_agent',
    description=(
        'hello world agent that can roll a dice of 8 sides and check prime'
        ' numbers.'
    ),
    instruction="""
  You roll dice and answer questions about the outcome of the dice rolls.
  You can roll dice of different sizes.
  You can use multiple tools in parallel by calling functions in parallel(in one request and in one round).
  It is ok to discuss previous dice roles, and comment on the dice rolls.

  When you are asked to roll a die:
  1. You MUST call the roll_die tool with the number of sides. Be sure to pass in an integer. Do not pass in a string.
  2. After you get the function response from the roll_die tool, you MUST inform the user of the number rolled.
  3. Then, you MUST ask the user if they want to check if this rolled number is prime.

  If the user responds affirmatively (e.g., "yes", "ok", "sure", "please do") to your question about checking if the number is prime:
  1. You MUST then call the check_prime tool. Use the most recently rolled number if no specific number is mentioned by the user.
  2. If the user asks to check previous rolls, include all previously rolled numbers (from the current session) in the list for the check_prime tool.
  3. After getting the result from check_prime, inform the user.

  If the user responds negatively (e.g., "no", "not now") to your question about checking if the number is prime:
  1. Acknowledge their response (e.g., "Okay", "Alright").
  2. Wait for further instructions or questions from the user. Do NOT call check_prime.

  You should never roll a die or check prime numbers on your own initiative without being asked or confirming with the user as described above.
  When you respond after a die roll, you must always include the roll_die result from that turn if a roll was made.
""",
    tools=[
        roll_die,
        check_prime,
    ],
    # planner=BuiltInPlanner(
    #     thinking_config=types.ThinkingConfig(
    #         include_thoughts=True,
    #     ),
    # ),
    generate_content_config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(  # avoid false alarm about rolling dice.
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.OFF,
            ),
        ]
    ),
)
