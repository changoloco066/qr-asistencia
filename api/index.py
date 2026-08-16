from flask import Flask

from api.auth import auth_bp
from api.roster import roster_bp
from api.sessions import sessions_bp
from api.checkin import checkin_bp

app = Flask(__name__)
app.register_blueprint(auth_bp)
app.register_blueprint(roster_bp)
app.register_blueprint(sessions_bp)
app.register_blueprint(checkin_bp)


@app.route("/api/health")
def health():
    return {"status": "ok"}