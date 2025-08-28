from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required

app = Flask(__name__)
app.config["SECRET_KEY"] = 'password'

login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, user_name, password_hash, email):
        self.id = id
        self.user_name = user_name
        self.password_hash = password_hash
        self.email = email

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    conn, cursor = db_connect()
    cursor.execute('select *from User where id = ?', (user_id,))
    result = cursor.fetchone()
    if result is not None:
        return User(result[0], result[1], result[2], result[3])
    return None


def db_connect():
    connection = sqlite3.connect('sqlite.db')
    cursor = connection.cursor()
    return connection, cursor


def db_disconnect(conn):
    conn.close()


@app.route("/")
def main():
    return render_template("index.html")


@app.route("/blog/")
def blog():
    print(request)
    conn, cursor = db_connect()
    cursor.execute('''SELECT post.id, post.title, post.content, post.author_id, user.user_name, count(post_like.id) as likes
    from post
    join user on post.author_id = user.id
    left join post_like on post.id = post_like.post_id
    group by
    post.id, post.title, post.content, post.author_id, user.user_name''')
    result = cursor.fetchall()
    posts = []
    for post in reversed(result):
        posts.append({
            'id': post[0],
            'title': post[1],
            'content': post[2],
            'author_id': post[3],
            'user_name': post[4],
            'likes': post[5]
        })
    user_likes = []
    if current_user.is_authenticated:
        cursor.execute('select post_id from post_like where user_id = ?', (current_user.id,) )
        likes_result = cursor.fetchall()
        for like in likes_result:
            user_likes.append(like[0])
    context = {'posts': posts,'user_likes': user_likes}
    return render_template("Blog.html", **context)


@app.route('/post_add/', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        conn, cursor = db_connect()
        cursor.execute('insert into post (title,content,author_id)values (?,?,?)',
                       (title, content, current_user.id))
        conn.commit()
        db_disconnect(conn)
        return redirect(url_for("blog"))
    return render_template('add_post.html', )


@app.route('/comment/<post_id>', methods = ['POST'])
def comment(post_id):
    if request.method == 'POST':
        comment = request.form['comment']
        conn, cursor = db_connect()
        cursor.execute('insert into post_comment (comment, post_id, user_id)values (?,?,?)',
                       (comment, post_id, current_user.id))
        conn.commit()
        db_disconnect(conn)
        return redirect(url_for('post', post_id=post_id))

@app.route('/post/<post_id>')
def post(post_id):
    conn, cursor = db_connect()
    cursor.execute('select*from post where id = ?', (post_id,))
    result = cursor.fetchone()
    post_data = {'id': result[0], 'title': result[1],
                 'content': result[2], 'author_id': result[3]}
    cursor.execute('select p.comment,u.user_name from post_comment as p join user as u on p.user_id=u.id where post_id = ?', (post_id,))
    result_1 = cursor.fetchall()
    comments = [
        {'comment': data[0],'username': data[1]} for data in result_1
    ]
    return render_template('post.html', post_data=post_data,comments=comments)



def user_like(post_id, user_id):
    conn, cursor = db_connect()
    cursor.execute('select * from post_like where user_id = ? and post_id = ?',
                   (user_id, post_id,))
    result = cursor.fetchone()
    return bool(result)

@app.route('/like/<int:post_id>')
@login_required
def like_post(post_id):
    conn, cursor = db_connect()
    post = cursor.execute('select * from post where id = ?', (post_id,)).fetchone()
    print(post)
    if post:
        if user_like(post_id, current_user.id):
            cursor.execute('delete from post_like where post_id = ? and user_id = ?', (post_id, current_user.id))
            conn.commit()
            print(f'{post_id} unliked')
        else:
            cursor.execute('insert into post_like (post_id, user_id) values (?,?)', (post_id, current_user.id,))
            conn.commit()
            print(f'{post_id} liked')
        return redirect(url_for('blog'))
    return 'post not found', 404


@app.route('/blog/register/', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        password = request.form['password']
        email = request.form['email']
        conn, cursor = db_connect()
        try:
            cursor.execute('insert into user (user_name,password_hash,email) values (?,?,?)',
                           (name, generate_password_hash(password, method='pbkdf2:sha256'), email))
            conn.commit()
            db_disconnect(conn)
            return redirect(url_for("blog"))
        except sqlite3.IntegrityError:
            return render_template('register.html', message="name or email is already taken")
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('blog'))

@app.route('/login/', methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        conn, cursor = db_connect()
        cursor.execute('select *from User where user_name = ?', (name,))
        result = cursor.fetchone()
        if result and User(result[0], result[1], result[2], result[3]).check_password(password):
            login_user(User(result[0], result[1], result[2], result[3]))
            return redirect(url_for('blog'))
        else:
             return  render_template('login.html', message='not true email or password')
    return render_template('login.html')

@app.route('/delete/<post_id>', methods=["POST"])
def delete(post_id):
    if request.method == 'POST':
        conn,cursor = db_connect()
        cursor.execute('delete from POST where id = ?', (post_id,))
        conn.commit()
        db_disconnect(conn)
        return redirect(url_for('blog'))

if __name__ == '__main__':
    app.run()
