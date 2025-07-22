#Flask signup form

from flask import Flask, request

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.subscriber_utils import add_subscriber

import re

app = Flask(__name__)

@app.route('/')
def index():
    return '''
        <h2> Subscribe to AI Market Digest</h2>
        <form method="POST" action="/subscribe">
            <input name="email" type="email" required placeholder="Enter your email" />
            <input type="submit" value="Subscribe" />
        </form>
    '''

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email', '').strip()
    
    # Validate email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Invalid email format. Please try again.", 400
    
    if add_subscriber(email):
        return f"{email} subscribed succesfully!", 200
    else:
        return f"{email} is already subscribed.", 200
    
if __name__ == "__main__":
    app.run(debug=True)