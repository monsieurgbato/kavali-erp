from flask import Blueprint

documents = Blueprint('documents', __name__)

from . import routes