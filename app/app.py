import os
import sys
import image
import search
import llm

from preflight import preflight
from util import *

def print_help_message():
    console.print("\nSwitch between two Main Modes:", style=f"bold {app_color}")
    console.print("'/search': Search for prompts (default mode)", style=f"{app_color}")  
    console.print("'/chat': Chat with Llama about the search results", style=f"{app_color}")

    console.print("\nSearch functions:", style=f"bold {app_color}")
    console.print("'/more': Next page in search results", style=f"{app_color}")
    console.print("'/page 4': Go to any specific page in results", style=f"{app_color}")
    console.print("'/filter your keywords, more': Filter search results (blank to remove)", style=f"{app_color}")

    console.print("\nImage functions:", style=f"bold {app_color}")
    console.print("'/1': Generate image from number prompt (/1,/54,etc)", style=f"{app_color}")
    console.print("'/random': Generate random image from search results", style=f"{app_color}")
    console.print("'/new': Llama creates a new prompt based on search", style=f"{app_color}")
    console.print("'/load': List and load image checkpoint models", style=f"{app_color}")
    console.print("'/aspect': Select some common aspect ratios", style=f"{app_color}")     

    console.print("\nSystem:", style=f"bold {app_color}")
    console.print("'/quit': Exit the program", style=f"{app_color}")
    console.print("'/wipe': Wipe (clear) the screen", style=f"{app_color}")
    console.print("'/help': Show this help message", style=f"{app_color}")

    console.print("\nNOTE: all of these commands may be shortened to one letter.\n\n", style=f"bold {app_color}")

#special command handling
class Command(Enum):
    ASPECT = auto() 
    CHAT = auto() 
    CONTINUE = auto()
    EXIT = auto()
    FILTER = auto()
    HELP = auto()
    LOAD = auto()
    MORE = auto()
    NEW = auto()
    NUMERIC = auto()
    PAGE = auto()
    RANDOM = auto()
    SEARCH = auto() 
    WIPE = auto()
    UNKNOWN = auto()

COMMAND_MAPPINGS = {
    'aspect': (['/aspect', '/a'], Command.ASPECT),
    'chat': (['/chat', '/c'], Command.CHAT),
    'exit': (['/bye', '/b', '/q', '/quit', '/e', '/exit'], Command.EXIT),
    'filter': (['/filter', '/f'], Command.FILTER),
    'help': (['/help', '/h'], Command.HELP),
    'load': (['/load', '/l'], Command.LOAD),
    'more': (['/more', '/m'], Command.MORE),
    'new': (['/new', '/n'], Command.NEW),
    'page': (['/page', '/p'], Command.PAGE),
    'random': (['/random', '/r'], Command.RANDOM),
    'wipe': (['/wipe', '/w'], Command.WIPE),
    'search': (['/search', '/s'], Command.SEARCH),
}

def handle_special_commands(user_input):
    lower_input = user_input.lower()
    
    for command_name, (command_aliases, command_enum) in COMMAND_MAPPINGS.items():
        for alias in command_aliases:
            if lower_input.startswith(alias + ' ') or lower_input == alias:
                if command_enum == Command.FILTER:
                    keywords = user_input[len(alias):].strip()
                    return command_enum, keywords
                elif command_enum == Command.ASPECT:
                    args = lower_input[len(alias):].strip()
                    if args:
                        try:
                            aspect_number = int(args)
                            return command_enum, aspect_number
                        except ValueError:
                            return Command.UNKNOWN
                    else:
                        return command_enum, None
                elif command_enum == Command.LOAD:
                    args = lower_input[len(alias):].strip()
                    if args:
                        try:
                            model_number = int(args)
                            return command_enum, model_number
                        except ValueError:
                            return Command.UNKNOWN
                    else:
                        return command_enum, None
                elif command_enum == Command.PAGE:
                    try:
                        page_number = int(user_input[len(alias):].strip())
                        return command_enum, page_number
                    except ValueError:
                        return Command.UNKNOWN
                return command_enum
    
    if lower_input.startswith('/'):
        if re.match(r'^/\d+$', lower_input):
            return Command.NUMERIC, int(lower_input[1:])
        return Command.UNKNOWN
    
    return None

#######################################################
###################  APP LOOP  ########################
#######################################################

def interactive_chat():
    sync_comments_config()

    os.system('cls' if os.name == 'nt' else 'clear')
    preflight()
    print_welcome_message()
    documents = []
    current_page = 1
    prompt_text = ""
    filter_text = ""
    chat_loop = False
    neural_searcher = search.NeuralSearcher(collection_name="prompts_large_meta")

            
    while True:

        if chat_loop:
            user_input = session.prompt("Chat with Llama about the results: ", style=style_llm)
        else:
            user_input = session.prompt("Enter new search terms or another command: ", style=style_search)
        
        user_input = user_input.strip()
        if not user_input:
            continue

        command = handle_special_commands(user_input)
        
        if isinstance(command, tuple):
            if command[0] == Command.NUMERIC:
                command_type, number = command
                image.prepare_image(documents, number=number)
            elif command[0] == Command.ASPECT:
                command_type, aspect_number = command
                if aspect_number is not None:
                    image.change_aspect(aspect_number)
                else:
                    image.list_aspect()
            elif command[0] == Command.FILTER:
                command_type, keywords = command
                filter_text = keywords
                current_page = 1
                documents = search.search_prompts(prompt_text, filter_text, neural_searcher)
                search.print_results(documents, prompt_text, filter_text, page=current_page)
            elif command[0] == Command.LOAD:
                command_type, model_number = command
                if model_number is not None:
                    image.change_model(model_number)
                else:
                    image.list_models()
            elif command[0] == Command.PAGE:
                command_type, page_number = command
                #check for valid page number in results range
                if not search.result_check(documents):
                    continue
                if 0 < page_number < ((len(documents['result']) / 5)+1):                
                    current_page = page_number
                    search.print_results(documents, prompt_text, filter_text, page=current_page)
                else:
                    console.print("\nclever girl! but no.\n--that's not a page number for these results.\n\n", style=f"bold {error_color}")

        elif command == Command.CHAT:
            if llm.preflight(documents):
                chat_loop = True

        elif command == Command.EXIT:
            return False

        elif command == Command.MORE:
            current_page += 1
            search.print_results(documents, prompt_text, filter_text, page=current_page)

        elif command == Command.NEW:
            if llm.preflight(documents):
                query = config('llm','image_prompt')
                response = llm.prepare_response(documents, query)
                if response is not False: 
                    llm_prompt = response
                    image.prepare_image(documents,llm_prompt=llm_prompt)

        elif command == Command.HELP:
            print_help_message()

        elif command == Command.RANDOM:
            number = 9999
            image.prepare_image(documents, number=number)

        elif command == Command.SEARCH:
            chat_loop = False

        elif command == Command.WIPE:
            os.system('cls' if os.name == 'nt' else 'clear')
            print_welcome_message()

        elif command == Command.UNKNOWN:
            print_help_message()
            
        else:
            # If it's not a command, treat it as new search / chat terms
            if chat_loop:
                query = user_input
                response = llm.prepare_response(documents, query)
                if response is not False: 
                    llm.print_response(response)

            else:
                prompt_text = user_input
                current_page = 1
                documents = search.search_prompts(prompt_text, filter_text, neural_searcher)
                search.print_results(documents, prompt_text, filter_text, page=current_page)

    return True

# Run the interactive chat
if __name__ == "__main__":
    interactive_chat()
