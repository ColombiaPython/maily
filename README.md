# Maily
Script to send automated emails with a google account.

1. Create an OAuth2.0 token here: [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
2. Store the Credentials on a file called: credentials.json
3. Create a venv:
```bash
python3 -m venv env
```
4. Activate the environment:
```bash
# Unix
source env/bin/activate

# Windows
env\Scripts\activate
```
5. Install the requirements:
```bash
pip install -r requirements.txt
```
6. Run the script:
```bash
python main.py
```