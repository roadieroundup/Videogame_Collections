from datetime import datetime
import os
import logging
from logging.handlers import RotatingFileHandler
import sqlalchemy as sa

import requests
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask.logging import default_handler
from werkzeug.security import generate_password_hash, check_password_hash

from forms import RegisterForm, LoginForm, NewListForm, AddForm, EditGameForm
from models import db, User, VideogameList, Videogame, login_user, LoginManager, current_user, \
    logout_user

AUTHORIZATION = f"Bearer {os.environ['ACCESS_TOKEN']}"

HEADERS = {"Client-ID": os.environ['CLIENT_ID'], "Authorization": AUTHORIZATION}

GAMES_URL = "https://api.igdb.com/v4/games/"

IMG_URL = "https://images.igdb.com/igdb/image/upload/t_1080p/"
SCREEN_URL = "https://images.igdb.com/igdb/image/upload/t_screenshot_big/"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ultrahipermegasecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL').replace("postgres://", "postgresql://", 1)
bootstrap = Bootstrap5(app)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)


# with app.app_context():
#     db.create_all()


def configure_logging(app):
    # Logging Configuration
    if app.config['LOG_WITH_GUNICORN']:
        gunicorn_error_logger = logging.getLogger('gunicorn.error')
        app.logger.handlers.extend(gunicorn_error_logger.handlers)
        app.logger.setLevel(logging.DEBUG)
    else:
        file_handler = RotatingFileHandler('instance/flask-user-management.log',
                                           maxBytes=16384,
                                           backupCount=20)
        file_formatter = logging.Formatter(
            '%(asctime)s %(levelname)s %(threadName)s-%(thread)d: %(message)s [in %(filename)s:%(lineno)d]')
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

    # Remove the default logger configured by Flask
    app.logger.removeHandler(default_handler)

    app.logger.info('Starting the Flask User Management App...')


engine = sa.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
inspector = sa.inspect(engine)
if not inspector.has_table("user"):
    with app.app_context():
        db.drop_all()
        db.create_all()
        app.logger.info('Initialized the database!')
else:
    app.logger.info('Database already contains the users table.')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}


@app.route("/", methods=["GET", "POST"])
def home():
    reg_form = RegisterForm()
    log_form = LoginForm()

    if reg_form.validate_on_submit():

        if User.query.filter_by(email=reg_form.email.data).first():
            flash("Email already in use")
            return redirect(url_for('home'))

        new_user = User(
            email=reg_form.email.data,
            password=generate_password_hash(reg_form.password.data, method='pbkdf2:sha256', salt_length=8),
            name=reg_form.name.data
        )

        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))

    elif log_form.validate_on_submit():
        email = log_form.email.data
        password = log_form.password.data

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Email does not exist")
            return redirect(url_for('home'))
        elif not check_password_hash(user.password, password):
            flash("Password incorrect")
            return redirect(url_for('home'))
        else:
            login_user(user)
            return redirect(url_for('home'))

    data = f'fields id,name,summary,cover.*,screenshots.*,first_release_date; where id = {ids_for_index()}; limit 15;'

    games = requests.post(GAMES_URL, headers=HEADERS, data=data).json()

    print(games)

    return render_template("index.html", games=games, reg_form=reg_form, log_form=log_form)


def today_to_unix():
    today = datetime.now()
    return int(today.timestamp())


def ids_for_index():
    today = today_to_unix()

    data = f'sort first_release_date desc;where aggregated_rating_count != 0 & first_release_date != null & first_release_date < {today} & cover != null & screenshots != null;limit 15;'

    ids = requests.post(GAMES_URL, headers=HEADERS, data=data).json()

    ids_tuple = tuple([value for dic in ids for value in dic.values()])

    return ids_tuple


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/user/<int:user_id>')
def profile(user_id):
    user = User.query.get(user_id)
    return render_template('profile.html', user=user)


@app.route('/delete_user/<int:user_id>/', methods=['GET', 'POST'])
def delete_user(user_id):
    if current_user.id != user_id:
        return login_manager.unauthorized()

    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/new_list/', methods=["GET", "POST"])
def new_list():
    if not current_user.is_authenticated:
        return login_manager.unauthorized()

    form = NewListForm()

    if form.validate_on_submit():
        n_list = VideogameList(
            name=form.name.data,
            description=form.description.data,
            img_url=form.img_url.data,
            author=current_user
        )

        db.session.add(n_list)
        db.session.commit()

        return redirect(url_for('profile', user_id=current_user.id))

    return render_template('new_list.html', form=form)


@app.route('/list/<int:list_id>')
def show_list(list_id):
    vg_list = VideogameList.query.get(list_id)

    if vg_list.is_sorted:
        games = vg_list.videogames

        games = sorted(games, key=lambda x: x.rating, reverse=True)

        return render_template('list.html', vg_list=vg_list, games=games)

    games = vg_list.videogames

    return render_template('list.html', vg_list=vg_list, games=games)


@app.route('/delete_list/<int:list_id>')
def delete_list(list_id):
    vg_list = VideogameList.query.get(list_id)

    if current_user.id != vg_list.author.id:
        return login_manager.unauthorized()

    db.session.delete(vg_list)
    db.session.commit()
    return redirect(url_for('profile', user_id=current_user.id))


@app.route('/edit_list/<int:list_id>', methods=["GET", "POST"])
def edit_list(list_id):
    vg_list = VideogameList.query.get(list_id)

    if current_user.id != vg_list.author.id:
        return login_manager.unauthorized()

    form = NewListForm(
        name=vg_list.name,
        description=vg_list.description,
        img_url=vg_list.img_url
    )

    if form.validate_on_submit():
        vg_list.name = form.name.data
        vg_list.description = form.description.data
        vg_list.img_url = form.img_url.data
        db.session.commit()

        return redirect(url_for('show_list', list_id=vg_list.id))

    return render_template('edit_list.html', form=form)


@app.route('/sort_list/<int:list_id>', methods=["GET", "POST"])
def sort_list(list_id):
    vg_list = VideogameList.query.get(list_id)

    if current_user.id != vg_list.author.id:
        return login_manager.unauthorized()

    vg_list.is_sorted = True
    db.session.commit()
    return redirect(url_for('show_list', list_id=list_id))


@app.route('/search_game/<int:list_id>', methods=["GET", "POST"])
def search_game(list_id):
    if not current_user.is_authenticated:
        return login_manager.unauthorized()

    form = AddForm()

    if form.validate_on_submit():
        game_title = form.title.data

        data = f'search "{game_title}";fields id,name,cover.*,release_dates.*;where release_dates.human != null & release_dates.date != null & cover != null; limit 20;'

        games = requests.post(GAMES_URL, headers=HEADERS, data=data).json()

        print(games)

        return render_template('results.html', games=games, list_id=list_id)

    return render_template('search_game.html', form=form, list_id=list_id)


@app.route('/add_game/<int:list_id>', methods=["GET", "POST"])
def add_game(list_id):
    vg_list = VideogameList.query.get(list_id)

    if current_user.id != vg_list.author.id:
        return login_manager.unauthorized()

    game_id = request.args.get('game_id')

    data = f'fields name,summary,cover.*, release_dates.*; where id = {game_id};'

    game_request = requests.post(GAMES_URL, headers=HEADERS, data=data).json()[0]

    description = game_request["summary"].split('.')[0]

    if len(description) > 200:
        description = description[:200] + '...'

    print("LIST ID")
    print(list_id)

    game = Videogame(
        title=game_request["name"],
        year=datetime.fromtimestamp(game_request["release_dates"][0]["date"]).year,
        description=description,
        img_url=IMG_URL + game_request["cover"]["image_id"] + ".png",
        list_id=list_id
    )

    db.session.add(game)
    db.session.commit()

    return redirect(url_for('edit_game', game_id=game.id))


@app.route('/edit_game/<int:game_id>', methods=["GET", "POST"])
def edit_game(game_id):
    game = Videogame.query.get(game_id)
    print(game)
    vg_list = VideogameList.query.get(game.list_id)
    print(vg_list)

    if current_user.id != vg_list.author_id:
        return login_manager.unauthorized()

    form = EditGameForm()

    if form.validate_on_submit():
        game = Videogame.query.get(game_id)
        game.rating = form.rating.data
        game.review = form.review.data

        db.session.commit()

        return redirect(url_for('show_list', list_id=game.list_id))

    return render_template('edit_game.html', form=form)


@app.route('/delete_game/<int:game_id>')
def delete_game(game_id):
    game = Videogame.query.get(game_id)

    if current_user.id != VideogameList.query.get(game.list_id).author_id:
        return login_manager.unauthorized()

    db.session.delete(game)
    db.session.commit()
    return redirect(url_for('show_list', list_id=game.list_id))


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
