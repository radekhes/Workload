from ecs.dbadmin_auth import AuthIndexView
from ecs.environment import configure_ecs_env
from ecs.umniverse import umniverse
from flask import Flask
from flask_admin import Admin
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask import Flask
from flask_mail import Mail, Message
from ecs.dbadmin_auth import AuthIndexView
from flask_admin import Admin
import config
from flask_admin import Admin

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)
Bootstrap(app)
CSRFProtect(app)
configure_ecs_env(app)
umniverse(app)
adminApp = Admin(app, index_view=AuthIndexView(url='/dbadmin'))

from main.views import main_views
app.register_blueprint(main_views)




