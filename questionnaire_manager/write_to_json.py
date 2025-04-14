import json

class WriteToJson:

    def __init__(self, api_response, file_name):
        self.api_response = api_response
        self.file_name = file_name
    def write_pretty_json(self):
        """
        Writes a given API response to a JSON file with pretty formatting.

    Parameters:
    api_response (dict or list): The JSON response from an API call.
    """
        try:
            # Write the JSON response to a file with pretty formatting
                with open(self.file_name, 'w') as json_file:
                    json.dump(self.api_response, json_file, indent=4)
                print(f"✓ API response has been written to {self.file_name} successfully.")
        except (TypeError, ValueError) as e:
            print(f"Error writing to JSON file: {e}")
        except IOError as e:
            print(f"File I/O error: {e}")