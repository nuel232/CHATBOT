from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"  # Secret key for session management
socketio = SocketIO(app)

rooms = {}  # Dictionary to store room information

# Function to generate a unique code for a room
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:  # Ensure the generated code is unique
            break

    return code

# Route for the home page
@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()  # Clear session data
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)  # Check if joining a room
        create = request.form.get("create", False)  # Check if creating a room

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)

        room = code
        if create != False:  # If creating a room, generate a unique code
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}  # Initialize room data
        elif code not in rooms:  # If joining and room doesn't exist
            return render_template("home.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room  # Store room and name in session
        session["name"] = name
        return redirect(url_for("room"))  # Redirect to room page

    return render_template("home.html")  # Render home page template

# Route for the room page
@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))  # Redirect to home if session data is invalid

    return render_template("room.html", code=room, messages=rooms[room]["messages"])  # Render room page template with room data

# SocketIO event handler for receiving messages
@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)  # Send message to everyone in the room
    rooms[room]["messages"].append(content)  # Add message to room's message history
    print(f"{session.get('name')} said: {data['data']}")  # Print message to console

# SocketIO event handler for client connection
@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)  # Join the room
    send({"name": name, "message": "has entered the room"}, to=room)  # Send message to room about new user
    rooms[room]["members"] += 1  # Increment member count of the room
    print(f"{name} joined room {room}")  # Print connection message to console

# SocketIO event handler for client disconnection
@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)  # Leave the room upon disconnection

    if room in rooms:
        rooms[room]["members"] -= 1  # Decrement member count of the room
        if rooms[room]["members"] <= 0:
            del rooms[room]  # Delete room if no members left

    send({"name": name, "message": "has left the room"}, to=room)  # Send message to room about user leaving
    print(f"{name} has left the room {room}")  # Print disconnection message to console

if __name__ == "__main__":
    # Run the Flask app with SocketIO support on port 5001 for the backup server
    socketio.run(app,  host='172.20.10.2', port=5001, debug=True)
