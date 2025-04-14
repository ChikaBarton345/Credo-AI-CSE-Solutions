import requests
import json
from dotenv import load_dotenv
import os

loaded = load_dotenv(dotenv_path=".env", override=True)


class TokenManager:
    def __init__(self, version: str):
        self.version = version

    def get_token(self):
        """
        Retrieves an access token from the Credo AI API using credentials from environment variables.
    
    Returns:
        str or None: The access token if successful, None if the request fails or token is not found
            in the response.
    
    Notes:
        - Requires API_KEY environment variable to be set
        - Makes a POST request to 'https://{BASE_PATH}/auth/exchange'
        - Automatically handles HTTP errors and JSON parsing
    
    Raises:
        requests.exceptions.HTTPError: If the HTTP request fails
        requests.exceptions.RequestException: For other request-related errors
        ValueError: If JSON parsing fails
    """
        print(f"=== Getting JWT_TOKEN  for {self.version} version of the questionnaire")
        if self.version == "new":            
            API_TOKEN = os.getenv("NEW_API_TOKEN")
            TENANT = os.getenv("NEW_TENANT")
            BASE_PATH = os.getenv("NEW_BASE_PATH")
        elif self.version == "old":
            API_TOKEN = os.getenv("OLD_API_TOKEN")
            TENANT = os.getenv("OLD_TENANT")
            BASE_PATH = os.getenv("OLD_BASE_PATH")

        url = f"{BASE_PATH}/auth/exchange"
        data = {
            "api_token": API_TOKEN,
            "tenant": TENANT
        }

        try:
            response = requests.post(url, json=data)
            response.raise_for_status()  
            token = response.json().get('access_token')
            
            if token:
                return token
            else:
                print('Access token not found in the response.')
                return None

        except requests.exceptions.HTTPError as http_err:
            print(f'HTTP error in get_token occurred: {http_err}')
        except requests.exceptions.RequestException as err:
            print(f'Other error in get_token occurred: {err}')
        except ValueError:
            print('Error parsing JSON response in get_token.')
        return None

    def write_token_to_file(self, token):
        """
        Writes or updates a jwt token to the .env file in the same directory as the script.
        
        Args:
            token (str): The jwt token to write to the .env file.
        
        Notes:
            - The token is written as 'JWT_TOKEN={token}' in the .env file
            - Preserves other existing environment variables in the .env file
            - Creates the .env file if it doesn't exist
            - Uses the script's directory as the location for the .env file
        
        Raises:
            IOError: If there are issues writing to the .env file
        """
        try:
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            env_path = os.path.join(script_dir, '.env')
            
            # Read existing .env file content
            env_content = {}
            try:
                with open(env_path, 'r') as file:
                    for line in file:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            env_content[key] = value
            except FileNotFoundError:
                pass  # File doesn't exist yet, will create it
            
            # Update or add the API_TOKEN
            if self.version == "new":
                env_content['NEW_JWT_TOKEN'] = token
            elif self.version == "old":
                env_content['OLD_JWT_TOKEN'] = token
            
            # Write back to .env file
            with open(env_path, 'w') as file:
                for key, value in env_content.items():
                    file.write(f'{key}={value}\n')
                print(f"Token written to '{env_path}' as JWT_TOKEN.")
        except IOError as e:
            print(f'Failed to write to .env file in write_token_to_file: {e}')

    def run(self):
        
        token = self.get_token()
        if token:
            self.write_token_to_file(token)
            return token
            
        else:
            print('Failed to obtain token, no value for JWT_TOKEN written to .env file.')

if __name__ == '__main__':
    token_manager = TokenManager(version="new")
    token_manager.run()
