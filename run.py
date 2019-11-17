from flask import Flask, render_template, request, g, redirect, url_for, session, make_response, jsonify
from flask_mail import Mail, Message
from random import *
import os
import flask_login
import json
from flask_pymongo import PyMongo, ObjectId

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://127.0.0.1:27017/likeBuds"
mongo = PyMongo(app)

app.config["MAIL_SERVER"]='smtp.gmail.com'  
app.config["MAIL_PORT"] = 465     
app.config["MAIL_USERNAME"] = 'flask.ganesh@gmail.com'
app.config['MAIL_PASSWORD'] = 'slmvveqoktmewnyf'
app.config['MAIL_USE_TLS'] = False  
app.config['MAIL_USE_SSL'] = True  

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
curr_user = ''
mail = Mail(app)
#otp = randint(000000,999999)
otp = 33333

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method=='POST':
        if request.form['revw']:
            msg = Message("Review from User:%s!"%(flask_login.current_user.id), sender = app.config["MAIL_USERNAME"], recipients = [app.config["MAIL_USERNAME"]])  
            msg.body = request.form['revw']
            mail.send(msg)
    return render_template('index.html')

@app.route('/ask', methods=['GET', 'POST'])
def ask():
    if flask_login.current_user.is_authenticated:
        return render_template('ask.html', user_email = flask_login.current_user.id)
    else:
        return render_template('login.html', arg = 'ask_qn')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method=='GET':
        return render_template('login.html')
    session['email']=request.form['email']
    email_dict = {"email": session['email']}
    print("email_dict:{}".format(email_dict))
    user = mongo.db.users.find_one(email_dict)
    if not user:
        return render_template('login.html', msg = 'Email doesn\'t exists! Please register if new user!')
    if user['passwd'] != request.form['passwd']:
        return render_template('login.html', msg = 'Password is incorrect!')
    user = User()
    user.id = session['email']
    flask_login.login_user(user)
    if 'ask' in request.form['arg']:
        return redirect(url_for('ask'))
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method=='GET':
        return render_template('register.html')
    else:
        session['email'] = request.form['email']
        session['user_info'] = {'email': str(session['email']), 'passwd': str(request.form['passwd']), 'uname': str(request.form['uname'])}
        re_passwd=request.form['re_passwd']
        if session['user_info']['passwd']==re_passwd:
            email_dict = {"email": session['email']}
            #handling if user(s) already exists
            for _ in mongo.db.users.find(email_dict):
                return render_template('register.html', msg = 'Email already used!!!')
            msg = Message('LikeBuds Account Verification', sender = app.config["MAIL_USERNAME"], recipients = [session['email']])  
            msg.body = str(otp)  
            mail.send(msg)
            return redirect(url_for('validate'))
        else:
            return render_template('register.html', msg = 'Password Doesn\'t matching!!!')

@app.route('/validate',methods=['GET', "POST"])
def validate():
    if request.method == 'GET':
        return render_template('validate_email.html')
    user_otp = request.form['otp']
    print("otps:{},{}".format(user_otp, otp))
    if otp == int(user_otp):
        mongo.db.users._insert(session['user_info'])
        print("redirecting to login.html")
        return render_template('login.html', msg = 'Registered Successfully! Please login')
    return render_template('validate_email.html', msg = 'OTP doesnot Matching!!!')

@app.route('/logout', methods=['GET', 'POST'])
@flask_login.login_required
def logout():
    flask_login.logout_user()
    session.clear()
    return redirect(url_for('index'))

#flask_login section
class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(email):
    user = User()
    user.id = session['email']
    return user

@flask_login.login_required
@app.route('/qn_post', methods = ['POST'])
def post_question():
    session['Tags'] = str(request.form['qn_tags']).split(',')
    session['qn_post'] = request.form['qn_post']
    session['qn_post_visible'] = request.form['qn_post_visible']
    if session['qn_post_visible'] == 'private':
        session['private_emails'] = str(request.form['pr_email']).split(',')
    else:
        session['private_emails'] = 'null'
    session['qn_created_on'] = request.form['browser_time']
    print("time:{}".format(request.form['browser_time']))
    post_dict = {'Tags': session['Tags'], 'qn_post': session['qn_post'], \
        'qn_post_visible': session['qn_post_visible'], 'private_emails': session['private_emails'], 'qn_created_on': session['qn_created_on'], 'owner_email':session['email']}
    mongo.db.posts.insert_one(post_dict)
    curr_post = mongo.db.posts.find_one({'qn_post':session['qn_post']})
    print("curr_post:{}".format(curr_post))
    session['cur_qn_post'] = {'qn_post':session['qn_post']}
    return render_template('post.html', cur_page_data=curr_post)

@app.route('/post_comment', methods = ['POST'])
@app.route('/post/<string>', methods = ['GET'])
def post(string = ""):
    if string:
        print("get executed!!")
        qn_post_dict = {'qn_post': string}
        session['cur_qn_post'] = qn_post_dict
        cur_post = mongo.db.posts.find_one(qn_post_dict)
    else:
        print("post executed!!")
        qn_post_dict = session['cur_qn_post']
        print("qn_dict:{}".format(qn_post_dict))
        cur_post = mongo.db.posts.find_one(qn_post_dict)
        comment_dict = {'post_id':str(cur_post['_id']),'comment': request.form['comment'], 'commenter':flask_login.current_user.id, 'commented_on': request.form['browser_time']}
        mongo.db.comments.insert_one(comment_dict)
    curr_qn_dict = {'post_id': str(cur_post['_id'])}
    curr_cmt = list(mongo.db.comments.find(curr_qn_dict))
    print(list(curr_cmt))
    return render_template('post.html', cur_page_data =cur_post, cur_page_cmt=curr_cmt)

@app.route('/posts', methods = ['GET'])
def posts():
    post_list = mongo.db.posts.find().sort('qn_created_on',-1).limit(5)
    return render_template('posts.html', cur_page_data=post_list)

if __name__ == '__main__':
    app.secret_key="afdoijaw23409aoj()_)(&%#$%)"
    app.run(debug=True, use_reloader=False)
