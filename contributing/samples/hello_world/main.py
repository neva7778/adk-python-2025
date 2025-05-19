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

import asyncio
import time

import agent
from dotenv import load_dotenv
from google.adk.agents.run_config import RunConfig
# from google.adk.cli.utils import logs # Mantenemos logs comentado
from google.adk.runners import InMemoryRunner
from google.adk.sessions import Session # Importante para type hint
from google.genai import types

load_dotenv(override=True)
# logs.log_to_tmp_folder() # Mantenemos esto comentado


async def main():
  app_name = 'my_app'
  user_id_1 = 'user1'
  runner = InMemoryRunner(
      agent=agent.root_agent,
      app_name=app_name,
  )
  session_11: Session = runner.session_service.create_session( # Añadí el type hint para claridad
      app_name=app_name, user_id=user_id_1
  )

  # ----- MODIFICACIÓN 1: Descomentar la función run_prompt -----
  async def run_prompt(current_session: Session, new_message: str): # Cambié 'session' a 'current_session' para evitar conflicto con el módulo 'session'
    content = types.Content(
        role='user', parts=[types.Part.from_text(text=new_message)]
    )
    print('** User says:', content.model_dump(exclude_none=True))
    async for event in runner.run_async(
        user_id=user_id_1,
        session_id=current_session.id, # Usar el id de la sesión pasada como argumento
        new_message=content,
    ):
      if event.content and event.content.parts and event.content.parts[0].text:
        print(f'** {event.author}: {event.content.parts[0].text}')
      # Aquí puedes añadir los prints opcionales para function_call si lo deseas para más detalle
      elif event.content and event.content.parts and event.content.parts[0].function_call:
        print(f'** {event.author} -> TOOL_CALL: {event.content.parts[0].function_call.name}({event.content.parts[0].function_call.args})')

#   async def run_prompt_bytes(session: Session, new_message: str):
#     content = types.Content(
#         role='user',
#         parts=[
#             types.Part.from_bytes(
#                 data=str.encode(new_message), mime_type='text/plain'
#             )
#         ],
#     )
#     print('** User says:', content.model_dump(exclude_none=True))
#     async for event in runner.run_async(
#         user_id=user_id_1,
#         session_id=session.id,
#         new_message=content,
#         run_config=RunConfig(save_input_blobs_as_artifacts=True),
#     ):
#       if event.content.parts and event.content.parts[0].text:
#         print(f'** {event.author}: {event.content.parts[0].text}')

# ----- MODIFICACIÓN 2: Cambiar el bloque de ejecución por un bucle interactivo -----
  start_time = time.time()
  print('Start time:', start_time)
  print('------------------------------------')
  
  # Iniciar la conversación con un saludo del agente (opcional)
  # O puedes permitir que el usuario ingrese el primer mensaje.
  await run_prompt(session_11, 'Hi') # Puedes mantener esto o comentarlo si quieres que el usuario empiece

  while True:
    try:
        user_input = input("User: ")
    except KeyboardInterrupt:
        print("\nSaliendo por petición del usuario (Ctrl+C).")
        break
    except EOFError:
        print("\nFin de la entrada detectado. Saliendo.")
        break 
      
    await run_prompt(session_11, user_input)


#   start_time = time.time()
#   print('Start time:', start_time)
#   print('------------------------------------')
#   await run_prompt(session_11, 'Hi')
#   await run_prompt(session_11, 'Roll a die with 100 sides')
#   await run_prompt(session_11, 'Roll a die again with 100 sides.')
#   await run_prompt(session_11, 'What numbers did I got?')
#   await run_prompt_bytes(session_11, 'Hi bytes')
#   print(
#       await runner.artifact_service.list_artifact_keys(
#           app_name=app_name, user_id=user_id_1, session_id=session_11.id
#       )
#   )


  end_time = time.time()
  print('------------------------------------')
  print('End time:', end_time)
  print('Total time:', end_time - start_time)


if __name__ == '__main__':
  asyncio.run(main())
