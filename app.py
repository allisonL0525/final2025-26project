# pls don't die
print("Hello!")

from flask import Flask, render_template
app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome to our Flash Web Application"

if __name__ == "__main__":
    app.run(debug=True)