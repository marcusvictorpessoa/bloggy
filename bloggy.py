from weppy import App, session, now, abort, redirect, url
from weppy.orm import Database, Model, Field, belongs_to, has_many
from weppy.tools.auth import AuthUser
from weppy.tools import Auth, requires
from weppy.sessions import SessionManager

app = App(__name__)

class User(AuthUser):
    has_many('posts', 'comments')

class Post(Model):
    belongs_to('user')
    has_many('comments')

    title = Field()
    text = Field.text()
    date = Field.datetime()

    default_values = {
        'user': lambda: session.auth.user.id,
        'date': lambda: now
    }
    validation = {
        'user': {'presence': True},
        'date': {'presence': True}
    }
    fields_rw = {
        'user': False,
        'date': False
    }

class Comment(Model):
    belongs_to('user', 'post')
    
    text = Field.text()
    date = Field.datetime()

    default_values = {
        'user': lambda: session.auth.user.id,
        'date': lambda: now
    }
    validation = {
        'text': {'presence': True}
    }
    fields_rw = {
        'user': False,
        'post': False,
        'date': False
    }

app.config.auth.single_template = True
app.config.auth.registration_verification = False
app.config.auth.hmac_key = "MassiveDynamicRules"

db = Database(app, auto_migrate=True)
auth = Auth(app, db, user_model=User)
db.define_models(Post, Comment)

# weppy --app bloggy.py setup
# weppy --app bloggy.py run
@app.command('setup')
def setup():
    user = User.create(
        email="marcus@teste.com",
        first_name="Marcus",
        last_name="Pessoa",
        password="12m34a56r"
    )
    admins = auth.create_group("admin")
    auth.add_membership(admins, user.id)
    db.commit()

app.pipeline = [
    SessionManager.cookies('Walternate'),
    db.pipe,
    auth.pipe
]

@app.route("/")
def index():
    posts = Post.all().select(orderby=~Post.date)
    return dict(posts=posts)

@app.route("/post/<int:pid>")
def one(pid):
    def _validate_comment(form):
        form.params.post = pid
    post = Post.get(pid)
    if not post:
        abort(404)
    comments = post.comments(orderby=~Comment.date)
    form = Comment.form(onvalidation=_validate_comment)
    if form.accepted:
        redirect(url('one', pid))
    return locals()

@app.route("/new")
@requires(lambda: auth.has_membership('admin'), url('index'))
def new_post():
    form = Post.form()
    if form.accepted:
        redirect(url('one', form.params.id))
    return dict(form=form)

auth_routes = auth.module(__name__)