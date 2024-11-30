import os
from uuid import uuid4
from flask import current_app as app
from flask import render_template, url_for, flash, redirect, request, Flask, session, jsonify, abort, send_from_directory
from flaskblog import app, firebase, login_manager
from flaskblog.forms import LoginForm, RegistrationRequestForm, MemberRegistrationForm, ResetPasswordRequestForm
from flask_login import login_user, current_user, logout_user, login_required, UserMixin
from flask_mail import Mail, Message
import firebase_admin
from firebase_admin import credentials, db, firestore, storage, auth
from werkzeug.utils import secure_filename
from datetime import datetime
import random
import string
import requests
from itsdangerous import URLSafeTimedSerializer
import cv2
import numpy as np
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model # type: ignore
import dlib
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
from PIL import Image
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip

# Firebase Admin SDK Initialization
cred = credentials.Certificate(r'C:\Users\huaweii\Downloads\shayek-560ec-firebase-adminsdk-b0vzc-d1533cb95f.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://shayek-560ec-default-rtdb.firebaseio.com/',
    'storageBucket': 'shayek-560ec.appspot.com'
})
firebase_database = db.reference()

detector = dlib.get_frontal_face_detector()

# Loading both models
def get_model_paths():
    current_dir = os.path.dirname(__file__)
    deepfake_model_path = os.path.join(current_dir, 'ResNet50_Model_DF.h5')
    faceswap_model_path = os.path.join(current_dir, 'ResNet50_Model_FS.h5')
    return deepfake_model_path, faceswap_model_path

deepfake_model_path, faceswap_model_path = get_model_paths()
deepfake_model = load_model(deepfake_model_path)
faceswap_model = load_model(faceswap_model_path)
    
UPLOAD_FOLDER = 'uploads'
STAMPED_FOLDER = 'flaskblog/static/stamped/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STAMPED_FOLDER, exist_ok=True)

def parse_timestamp(timestamp):
    try:
        return datetime.strptime(timestamp, '%b %d, %Y %I:%M%p')
    except (ValueError, TypeError):
        return datetime(1970, 1, 1)

def fetch_posts():
    posts_ref = db.reference('posts')
    posts_snapshot = posts_ref.get()
    posts = [(post_id, posts_snapshot[post_id]) for post_id in posts_snapshot]
    posts.sort(key=lambda post: parse_timestamp(post[1]['timestamp']), reverse=True)

    formatted_posts = []
    for post_id, post_data in posts:
        count = 0
        comments = post_data.get('comment', {})
        formatted_comments = []   
        
        if isinstance(comments, dict):
            for comment_id, comment_data in comments.items():
                count += 1
                if comment_data:
                    replies = comment_data.get('replies', {})
                    formatted_replies = []
                    
                    if isinstance(replies, dict):
                        sorted_replies = sorted(replies.items(), key=lambda x: parse_timestamp(x[1].get('timestamp', '')))
                        
                        for reply_id, reply in sorted_replies:
                            formatted_reply = {
                                'author': reply.get('author', ''),
                                'author_email': reply.get('author_email', ''),
                                'body': reply.get('body', ''),
                                'reply_id': reply.get('reply_id', ''),
                                'timestamp': reply.get('timestamp', '')
                            }
                            formatted_replies.append(formatted_reply)
                    
                    comment_data['replies'] = formatted_replies
                formatted_comments.append(comment_data)

        formatted_posts.append({
            'post_id': post_id,
            'author': post_data.get('author'),
            'author_email': post_data.get('author_email'),
            'timestamp': post_data.get('timestamp'),
            'title': post_data.get('title'),
            'content': post_data.get('body'),
            'media': post_data.get('media_url'),
            'comments': formatted_comments,
            'count': count,
            'likes': post_data.get('likes', 0),  
            'liked_by': post_data.get('liked_by', [])
        })
    
    return formatted_posts

posts = fetch_posts()

def fetch_posts_by_user(user_email):
    posts_ref = db.reference('posts').order_by_child('author_email').equal_to(user_email)
    posts_snapshot = posts_ref.get()
    if not posts_snapshot:
        return []
    
    posts = []
    for post_id, post_data in posts_snapshot.items():
        count = 0
        comments = post_data.get('comment', {})
        if isinstance(comments, dict):
            count = len(comments)

        parsed_timestamp = parse_timestamp(post_data.get('timestamp'))
        posts.append({
            'post_id': post_id,
            'author': post_data.get('author'),
            'author_email': post_data.get('author_email'),
            'timestamp': post_data.get('timestamp'),
            'parsed_timestamp': parsed_timestamp,
            'title': post_data.get('title'),
            'content': post_data.get('body'),
            'media': post_data.get('media_url'),
            'count': count,
            'likes': post_data.get('likes', 0),
            'liked_by': post_data.get('liked_by', [])
        })
    posts.sort(key=lambda x: x['parsed_timestamp'], reverse=True)

    return posts

def encode_email(email):
    return email.replace('.', 'dot').replace('@', 'at')

@app.route('/')
@app.route('/homepage')
def homepage():
    posts = fetch_posts()
    total_posts = len(posts)
    return render_template('homepage.html', posts=posts, total_posts=total_posts)

@app.route('/about')
def about():
    return render_template('about.html', title = 'من نحن؟')

def extract_and_preprocess_frames(video_path, max_frames=10, target_size=(299, 299)):
    cap = cv2.VideoCapture(video_path)
    frames = []
    processed_frames = []
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, frame_count // max_frames)
    blank_frame_count = 0
    max_blank_frames=4

    for i in range(0, frame_count, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        success, frame = cap.read()
        if success:
            frames.append(frame)
        if len(frames) == max_frames:
            break

    for frame in frames:
        detected_faces = detector(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        
        if detected_faces:
            face = detected_faces[0]
            x1, y1, x2, y2 = face.left(), face.top(), face.right(), face.bottom()
            cropped_face = frame[y1:y2, x1:x2]
            resized_face = cv2.resize(cropped_face, target_size)
            processed_frames.append(resized_face)
            blank_frame_count = 0
        else:
            processed_frames.append(np.zeros((target_size[0], target_size[1], 3), dtype=np.uint8))
            blank_frame_count += 1 
            
            if blank_frame_count > max_blank_frames:
                print("No faces detected for too long. Stopping processing.")
                break

    cap.release()
    return np.array(processed_frames)

@app.route('/shayekModel', methods=['GET', 'POST'])
def shayekModel():
    if request.method == 'POST':
        if request.files:
            video = request.files['video']
            if video and video.filename != '':
                upload_folder = 'uploads'
                os.makedirs(upload_folder, exist_ok=True)
                video_path = os.path.join(upload_folder, video.filename)
                video.save(video_path)
                
                processed_frames = extract_and_preprocess_frames(video_path)
                if processed_frames.size == 0:
                    os.remove(video_path)
                    return jsonify({'error': 'لم نستطع إيجاد وجوه ', 'code': 0})
                processed_frames = np.expand_dims(processed_frames, axis=0)

                # Making predictions using both models:
                deepfake_pred = deepfake_model.predict(processed_frames)[0][0]
                faceswap_pred = faceswap_model.predict(processed_frames)[0][0]

                # If either model predicts as manipulated, classify as so
                if deepfake_pred > 0.5 or faceswap_pred > 0.5:
                    pred_label = 'الفيديو معدل'
                    code = 2
                else:
                    pred_label = 'الفيديو حقيقي'
                    code = 1

                os.remove(video_path)

                return jsonify({'result': pred_label, 'code': code})
            return jsonify({'error': 'لم يتم إرفاق ملف أو الملف المرفق تالف', 'code': 0})

    return render_template('shayekModel.html', title='نشيّك؟', code=1)

@app.route('/delete_video', methods=['POST'])
def delete_video():

    video_path = request.json.get('video_path')
    if not video_path:
        return jsonify({'error': 'No video path provided'}), 400

    try:
        stamped_path = os.path.join(STAMPED_FOLDER, video_path)
        if os.path.exists(stamped_path):
            os.remove(stamped_path)
            return jsonify({'success': 'Video deleted successfully'})
        else:
            return jsonify({'error': 'Video not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/video_stamp', methods=['POST'])
def video_stamp():
    if 'video' not in request.files:
        return jsonify({"error": "لم يتم رفع الفيديو"}), 400

    video_file = request.files['video']

    if not video_file.filename.endswith('.mp4'):
        return jsonify({"error": "ملف الفيديو يجب أن يكون بصيغة .mp4"}), 400

    code = request.form.get('code', type=int)

    video_path = os.path.join(UPLOAD_FOLDER, video_file.filename)
    video_file.save(video_path)

    if code == 1:
        stamp_image_path = 'flaskblog/static/images/true.png'
    elif code == 2:
        stamp_image_path = 'flaskblog/static/images/false.png'
    else:
        stamp_image_path = 'flaskblog/static/images/false.png'

    try:
        cap = cv2.VideoCapture(video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        output_width = min(width, 1080)
        output_height = int(output_width * (height / width))

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        stamped_filename = f"{uuid.uuid4()}_stamped.mp4"
        stamped_path = os.path.join(STAMPED_FOLDER, stamped_filename)

        out = cv2.VideoWriter(stamped_path, fourcc, fps, (output_width, output_height))

        stamp = cv2.imread(stamp_image_path, cv2.IMREAD_UNCHANGED)
        if stamp is None:
            return jsonify({"error": "لم يتم العثور على صورة الختم"}), 400

        stamp_height = 350
        scale = stamp_height / stamp.shape[0]
        stamp_rgb = cv2.resize(stamp, (int(stamp.shape[1] * scale), int(stamp.shape[0] * scale)))

        stamp_height, stamp_width = stamp_rgb.shape[:2]

        if stamp_rgb.shape[2] == 4:
            alpha_channel = stamp_rgb[:, :, 3]
            stamp_rgb = stamp_rgb[:, :, :3]
        else:
            alpha_channel = None

        stamp_x = (output_width - stamp_width) // 2
        stamp_y = (output_height - stamp_height) // 2

        if stamp_x < 0 or stamp_y < 0:
            return jsonify({"error": "صورة الختم أكبر من إطار الفيديو"}), 400

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (output_width, output_height))

            if alpha_channel is not None:
                for c in range(3):
                    frame[stamp_y:stamp_y + stamp_height, stamp_x:stamp_x + stamp_width, c] = \
                        (stamp_rgb[:, :, c] * (alpha_channel / 255.0) +
                         frame[stamp_y:stamp_y + stamp_height, stamp_x:stamp_x + stamp_width, c] * (1.0 - alpha_channel / 255.0))
            else:
                frame[stamp_y:stamp_y + stamp_height, stamp_x:stamp_x + stamp_width] = stamp_rgb

            out.write(frame)

        cap.release()
        out.release()

        stamped_compressed_path = os.path.join(STAMPED_FOLDER, f"compressed_{stamped_filename}")
        with VideoFileClip(stamped_path) as video_clip:
            video_clip.write_videofile(stamped_compressed_path, bitrate="500k")

        os.remove(stamped_path)
        os.remove(video_path)

        return jsonify({"watermarked_video_path": f"compressed_{stamped_filename}", "code": code}), 200

    except Exception as e:
        return jsonify({"error": f"خطأ أثناء ختم الفيديو: {str(e)}"}), 500
    
@app.route('/home', methods=['GET'])
@login_required
def home():
    user_email = session.get('user_email') 
    filter_option = request.args.get('filter', 'followed')  

    if user_email:
        user_data = load_user(user_email)
        
        if user_data:
            login_user(user_data)
            newsoutlet_ref = db.reference('newsoutlet').order_by_child('email').equal_to(user_email).get()

            if newsoutlet_ref:
                user_info = list(newsoutlet_ref.values())[0]
                username = user_info.get('username')

                if filter_option == 'followed':
                    followed_users_ref = db.reference('follows').order_by_child('member_id').equal_to(current_user.email).get()
                    followed_users_emails = {user: data.get('newsoutlet_id') for user, data in followed_users_ref.items() if data.get('newsoutlet_id')} if followed_users_ref else {}

                    posts = []
                    for user_id, newsoutlet_id in followed_users_emails.items():
                        user_posts = fetch_posts_by_user(newsoutlet_id)
                        if user_posts:
                            posts.extend(user_posts)
                else:
                    posts = fetch_posts()
                total_posts = len(posts)
                print(total_posts)
                return render_template('newsoutlet_home.html', posts=posts, user=user_data, username=username, filter=filter_option, total_posts=total_posts)

            else: 
                member_ref = db.reference('members').order_by_child('email').equal_to(user_email).get()
                if member_ref:
                    user_info = list(member_ref.values())[0]
                    username = user_info.get('username')
                    if filter_option == 'followed':
                        followed_users_ref = db.reference('follows').order_by_child('member_id').equal_to(current_user.email).get()
                        followed_users_emails = {user: data.get('newsoutlet_id') for user, data in followed_users_ref.items() if data.get('newsoutlet_id')} if followed_users_ref else {}

                        posts = []
                        for user_id, newsoutlet_id in followed_users_emails.items():
                            user_posts = fetch_posts_by_user(newsoutlet_id)
                            if user_posts:
                                posts.extend(user_posts)
                    else:
                        posts = fetch_posts()
                    total_posts = len(posts)
                    return render_template('member_home.html', posts=posts, user=user_data, username=username, filter=filter_option, total_posts=total_posts)

                else:
                    flash('<i class="fas fa-times-circle me-3"></i> المستخدم غير موجود', 'danger')
                    return redirect(url_for('Member_login'))        
        else:
            flash('<i class="fas fa-times-circle me-3"></i> يرجى تسجيل الدخول أولاً', 'danger')
            return redirect(url_for('Member_login'))    
    else:
        flash('<i class="fas fa-times-circle me-3"></i> يرجى تسجيل الدخول أولاً', 'danger')
        return redirect(url_for('Member_login'))

@app.route('/member_login', methods=['GET', 'POST'])
def member_login():
    form = LoginForm()
    if form.validate_on_submit():
        api_key = "AIzaSyAXgzwyWNcfI-QSO_IbBVx9luHc9zOUzeY"
        request_payload = {
            "email": form.email.data,
            "password": form.password.data,
            "returnSecureToken": True
        }
        try:
            response = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}", json=request_payload)
            response.raise_for_status()
            user_info = response.json()

            user_email = user_info['email']
            user_id = user_info['localId']

            user_ref = db.reference('members').order_by_child('email').equal_to(user_email).get()

            if user_ref:
                user_data = list(user_ref.values())[0]
                user = load_user(user_email)

                if user:
                    login_user(user)
                    session['user_email'] = user_email
                    session['logged_in'] = True
                    session['user_type'] = 'member'
                    session['username'] = user_data.get('username')

                    flash('<i class="fas fa-check-circle me-3" style="color: green;"></i> تم تسجيل دخولك بنجاح', 'success')
                    return redirect(url_for('home'))
                else:
                    flash('<i class="fas fa-times-circle me-3"></i> الحساب غير موجود.', 'danger')

            else:
                flash('<i class="fas fa-times-circle me-3"></i> الحساب غير موجود.', 'danger')

        except requests.exceptions.HTTPError as e:
            try:
                error_json = e.response.json()
                error_message = error_json.get('error', {}).get('message', 'مشكلة غير معروفة')
            except ValueError:
                error_message = "حدثت مشكلة أثناء المعالجة، فضلًا حاول مجددًا."
            flash(f'<i class="fas fa-times-circle me-3"></i> {error_message}', 'danger')

        except ValueError:
            flash('<i class="fas fa-times-circle me-3"></i> حدثت مشكلة أثناء المعالجة، فضلًا حاول مجددًا.', 'danger')

    return render_template('member_login.html', title='تسجيل دخول الأعضاء', form=form)

@app.route('/newsoutlet_login', methods=['GET', 'POST'])
def newsoutlet_login():
    form = LoginForm()
    if form.validate_on_submit():
        api_key = "AIzaSyAXgzwyWNcfI-QSO_IbBVx9luHc9zOUzeY"
        request_payload = {
            "email": form.email.data,
            "password": form.password.data,
            "returnSecureToken": True
        }
        try:
            response = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}", json=request_payload)
            response.raise_for_status()
            user_info = response.json()

            user_email = user_info['email']
            user_id = user_info['localId']

            newsoutlet_ref = db.reference('newsoutlet').order_by_child('email').equal_to(user_email).get()

            if newsoutlet_ref:
                user_data = list(newsoutlet_ref.values())[0]
                user = load_user(user_email)

                if user:
                    login_user(user)
                    session['user_email'] = user_email
                    session['logged_in'] = True
                    session['user_type'] = 'newsoutlet'
                    session['username'] = user_data.get('username')

                    flash('<i class="fas fa-check-circle me-3" style="color: green;"></i> تم تسجيل دخولك بنجاح', 'success')
                    return redirect(url_for('home'))
                else:
                    flash('<i class="fas fa-times-circle me-3"></i> الحساب غير موجود.', 'danger')

            else:
                flash('<i class="fas fa-times-circle me-3"></i> الحساب غير موجود.', 'danger')

        except requests.exceptions.HTTPError as e:
            try:
                error_json = e.response.json()
                error_message = error_json.get('error', {}).get('message', 'مشكلة غير معروفة')
            except ValueError:
                error_message = "حدثت مشكلة أثناء المعالجة، فضلًا حاول مجددًا."
            flash(f'<i class="fas fa-times-circle me-3"></i> {error_message}', 'danger')

        except ValueError:
            flash('<i class="fas fa-times-circle me-3"></i> حدثت مشكلة أثناء المعالجة، فضلًا حاول مجددًا.', 'danger')

    return render_template('newsoutlet_login.html', title='تسجيل دخول المنصة الإعلامية', form=form)

def fetch_liked_posts(user_email):
    posts_ref = db.reference('posts')
    liked_posts = []

    all_posts = posts_ref.get() or {}
    for post_id, post_data in all_posts.items():
        liked_by = post_data.get('liked_by', [])
        
        if user_email in liked_by:
            post_data['post_id'] = post_id

            comments = post_data.get('comment', {})
            count = 0
            if isinstance(comments, dict):
                count = len(comments)

            post_data['count'] = count
            liked_posts.append(post_data)
            liked_posts.sort(key=lambda post: parse_timestamp(post.get('timestamp', '')), reverse=True)

    return liked_posts

@app.route('/profile')
@login_required
def profile():
    user_email = current_user.get_id()
    if not user_email:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح بها', 'danger')
        return redirect(url_for('newsoutlet_login'))

    user_ref = db.reference('newsoutlet').order_by_child('email').equal_to(user_email).get()
    user_type = 'newsoutlet' if user_ref else 'member'

    if user_type == 'member':
        user_ref = db.reference('members').order_by_child('email').equal_to(user_email).get()
        if not user_ref:
            flash('<i class="fas fa-times-circle me-3"></i> المستخدم غير موجود', 'danger')
            return redirect(url_for('member_login'))

    username = list(user_ref.values())[0].get('username')
    posts = fetch_posts_by_user(user_email)
    liked_posts = fetch_liked_posts(user_email)
    
    followed_news_outlets = []
    followed_users_ref = db.reference('follows').order_by_child('member_id').equal_to(current_user.email).get()


    if followed_users_ref:
        for data in followed_users_ref.values():
            email = data.get('newsoutlet_id')
            if email:
                user_ref = db.reference('newsoutlet').order_by_child('email').equal_to(email).get()
                if user_ref:
                    followed_username = list(user_ref.values())[0].get('username')
                    if followed_username != username:
                        followed_news_outlets.append(followed_username)

    if user_type == 'newsoutlet':
        news_outlet_email = current_user.email  
        news_outlet_ref = db.reference('newsoutlet').order_by_child('email').equal_to(news_outlet_email).get()

        followers_usernames = []

        if news_outlet_ref:
            for news_outlet in news_outlet_ref.values():
                followers = news_outlet.get('followers', [])
                
                for follower in followers:
                    if isinstance(follower, dict):
                        member_email = follower.get('member_id')
                        if member_email:
                            result = db.reference('members').order_by_child('email').equal_to(member_email).get()
                            if not result:
                                result = db.reference('newsoutlet').order_by_child('email').equal_to(member_email).get()

                            if result:
                                user_data = next(iter(result.values()), None)
                                follower_username = user_data.get('username')

                                if follower_username != username:
                                    followers_usernames.append(follower_username)

        return render_template('newsoutlet_myprofile.html', 
                            user_info=username, 
                            followers=followers_usernames, 
                            followed_news_outlets=followed_news_outlets, 
                            posts=posts,
                            liked_posts=liked_posts)

    return render_template(
        'member_myprofile.html',
        user_info=username,
        followed_news_outlets=followed_news_outlets,
        liked_posts=liked_posts
    )

@app.route('/profile/<username>')
def user_profile(username):
    user = None
    current_user_email = session.get('user_email')  

    newsoutlet_ref = firebase_database.child('newsoutlet')
    newsoutlet_data = newsoutlet_ref.get()

    if newsoutlet_data:
        for uid, userdata in newsoutlet_data.items():
            if userdata.get('username') == username:
                user = {
                    'id': userdata.get('id'),
                    'username': userdata.get('username'),
                    'email': userdata.get('email'),
                    'followers': userdata.get('followers', []),
                    'notifications': userdata.get('notifications', [])
                }

                useremail = user['email']
                posts = fetch_posts_by_user(useremail)
                current_followers = user['followers']
                current_notifications = user['notifications']

                followers_usernames = []
                for follower in current_followers:
                    if isinstance(follower, dict):
                        member_email = follower.get('member_id')
                        if not member_email:
                            continue

                        
                        result = db.reference('members').order_by_child('email').equal_to(member_email).get()
                        if not result:
                            result = db.reference('newsoutlet').order_by_child('email').equal_to(member_email).get()

                        if result:
                            user_data = next(iter(result.values()), None)
                            if user_data:
                                followers_usernames.append(user_data.get('username'))
                            else:
                                followers_usernames.append(member_email)  

               
                is_following = False
                is_getting_notifications = False
                followed_news_outlets = []

                
                if current_user_email:
                    is_following = any(
                        isinstance(follower, dict) and follower.get('member_id') == current_user_email
                        for follower in current_followers
                    ) if isinstance(current_followers, list) else False

                    is_getting_notifications = any(
                        isinstance(notification, dict) and notification.get('member_id') == current_user_email
                        for notification in current_notifications
                    )

                    
                    followed_users_ref = db.reference('follows').order_by_child('member_id').equal_to(useremail).get()
                    if followed_users_ref:
                        for data in followed_users_ref.values():
                            newsoutlet_email = data.get('newsoutlet_id')
                            if newsoutlet_email:
                                newsoutlet_ref = db.reference('newsoutlet').order_by_child('email').equal_to(newsoutlet_email).get()
                                if newsoutlet_ref:
                                    followed_news_outlets.append(list(newsoutlet_ref.values())[0].get('username'))

                followers_count = len([f for f in current_followers if isinstance(f, dict)])

                return render_template(
                    'newsoutlet_profile.html',
                    user_info=username,
                    posts=posts,
                    useremail=useremail,
                    followers=followers_usernames,
                    followers_count=followers_count,
                    followed_news_outlets=followed_news_outlets,
                    is_following=is_following,
                    is_getting_notifications=is_getting_notifications
                )

    member_ref = firebase_database.child('members')
    member_data = member_ref.get()

    if member_data:
        for uid, userdata in member_data.items():
            if userdata.get('username') == username:
                user = {
                    'id': userdata.get('id'),
                    'username': userdata.get('username'),
                    'email': userdata.get('email')
                }

                followed_news_outlets = []
                if current_user_email:
                 
                    followed_users_ref = db.reference('follows').order_by_child('member_id').equal_to(user['email']).get()
                    if followed_users_ref:
                        for data in followed_users_ref.values():
                            newsoutlet_email = data.get('newsoutlet_id')
                            if newsoutlet_email:
                                newsoutlet_ref = db.reference('newsoutlet').order_by_child('email').equal_to(newsoutlet_email).get()
                                if newsoutlet_ref:
                                    followed_news_outlets.append(list(newsoutlet_ref.values())[0].get('username'))

                return render_template(
                    'member_profile.html',
                    user_info=user['username'],
                    followed_news_outlets=followed_news_outlets
                )

    
    flash('لم نستطع إيجاد الحساب.', 'danger')
    return redirect(request.referrer)

def determine_user_role(email):
    users_ref = db.reference('members')
    users_query_result = users_ref.order_by_child('email').equal_to(email).get()
    if users_query_result:
        return 'user'
    admins_ref = db.reference('admins')
    admins_query_result = admins_ref.order_by_child('email').equal_to(email).get()
    if admins_query_result:
        return 'admin'
    return None  

@app.route('/member_register', methods=['GET', 'POST'])
def member_register():
    form = MemberRegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        try:
            user = auth.create_user(
                email=email,
                password=password
            )

            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            
            user_data = {
                'username': username,
                'email': email,
                'password' : hashed_password,
                'is_newsoutlet': False 
            }
            
            db.reference(f'members/{user.uid}').set(user_data)
            
            flash('<i class="fas fa-check-circle me-3" style="color: green;"></i> تم تسجيل الحساب بنجاح', 'success')
            return redirect(url_for('member_login'))
        except Exception as e:
            flash(f'<i class="fas fa-times-circle me-3"></i> حدث خطأ: {str(e)}', 'danger')

    return render_template('member_register.html', form=form)

@app.route('/register_request', methods=['GET', 'POST'])
def register_request():
    form = RegistrationRequestForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        company_name = form.company_name.data
        company_docs = request.files.get('company_docs')
        file_url = upload_file_to_firebase_storage(company_docs)

        registration_data = {
            'username': username,
            'email': email,
            'password': password,
            'company_name': company_name,
            'company_docs_url': file_url,
            'status' : 'under review'
        }

        db.reference('registration_requests').push(registration_data)

        flash('<i class="fas fa-check-circle me-3" style="color: green;"></i> تم رفع طلبكم بنجاح، سيتم مراجعة طلبكم والتأكد من الوثائق المرفقة، الرجاء مراجعة بريدكم الوارد أو البريد غير الهام خلال الأيام القادمة لمعرفة حالة الطلب', 'success')
        return redirect(url_for('homepage'))
    else:
        return render_template('register_request.html', title='طلب تسجيل حساب', form=form)

@login_manager.user_loader
def load_user(email):
    user_ref = db.reference('newsoutlet').order_by_child('email').equal_to(email).get()
    if user_ref:
        user_data = next(iter(user_ref.values()), None)
        if user_data:
            user_data.pop('email', None)
            password_hash = user_data.pop('password', None)
            if password_hash:
                return User(email=email, password_hash=password_hash, **user_data)

    user_ref = db.reference('members').order_by_child('email').equal_to(email).get()
    
    if user_ref:
        user_data = next(iter(user_ref.values()), None)
        if user_data:
            user_data.pop('email', None)
            password_hash = user_data.pop('password', None)
            if password_hash:
                return User(email=email, password_hash=password_hash, **user_data) 
    flash('<i class="fas fa-times-circle me-3"></i> مشكلة في بيانات المستخدم، الرجاء المحاولة لاحقاً', 'danger')
    return None

class User(UserMixin):
    def __init__(self, email, password_hash, username=None, is_active=True, **kwargs):
        self.id = email
        self.email = email
        self.username = username or kwargs.get('username')
        self.password_hash = password_hash
        self.is_active = is_active

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value

    def get_id(self):
        return self.id 
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'shayekgp1@gmail.com'
app.config['MAIL_PASSWORD'] = 'ymujhammpqswenzl'
app.config['MAIL_DEFAULT_SENDER'] = 'shayekgp1@gmail.com'

mail = Mail(app)

@app.route('/verify_request/<request_id>', methods=['POST'])
def verify_request(request_id):
    if 'logged_in' in session and session['role'] == 'admin':
        ref_request = db.reference(f'registration_requests/{request_id}')
        request_data = ref_request.get()

        if request_data:
            email = request_data['email']
            subject = ""
            body = ""
            password_hash = generate_password_hash(request_data['password']) 

            if 'decline' in request.form:
                ref_request.update({'status': 'declined', 'password': password_hash})
                subject = "رفض طلب تسجيل في منصة شيّــك"
                body = "عزيزنا/عزيزتنا {},\n\n" \
                       "نأسف لإشعاركم أنه لم يتم قبول طلب تسجيلكم في منصة شيّــك، " \
                       "الرجاء مراجعة الملف المرفق والتأكد من اكتمال المتطلبات وصحتها.".format(request_data['username'])

                flash('<i class="fas fa-check-circle me-3"></i> تم رفض الطلب بنجاح', 'info')
            elif 'accept' in request.form:
                new_user = auth.create_user(
                    email=request_data['email'],
                    password=request_data['password'],
                )
                user_data = {
                    'username': request_data['company_name'],
                    'email': request_data['email'],
                    'password': password_hash,
                    'is_newsoutlet': True
                }
                db.reference('newsoutlet').push(user_data)
                ref_request.update({'status': 'accepted', 'uid': new_user.uid, 'password': password_hash})                    
                subject = "تم قبول طلب تسجيلكم في منصة شيّــك"
                body = "عزيزنا/عزيزتنا {},\n\nتم قبول طلب تسجيلكم في منصة شيّــك".format(request_data['username'])
                flash('<i class="fas fa-check-circle me-3" style="color: green;"></i> تم قبول طلب التسجيل وإنشاء الحساب', 'success')
            msg = Message(subject, recipients=[email], body=body)
            mail.send(msg)
            return f"<script>window.location.href = '{url_for('admin_dashboard')}';</script>"
        else:
            flash('<i class="fas fa-times-circle me-3"></i> لم نستطع إيجاد أي بيانات.', 'danger')
            return redirect(url_for('admin_dashboard'))
    else:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح بها', 'danger')
        return redirect(url_for('member_login'))

def fetch_username_from_database(email):
    user_ref = db.reference('members').order_by_child('email').equal_to(email).get()
    if user_ref:
        user_data = next(iter(user_ref.values()))
        return user_data.get('username', None)
    else:
        return None

def upload_file_to_firebase_storage(file):
    if file:
        filename = secure_filename(file.filename)
        bucket = storage.bucket()
        blob = bucket.blob(f"company_docs/{filename}")
        blob.upload_from_string(file.read(), content_type=file.content_type)
        blob.make_public()
        return f"gs://shayek-560ec.appspot.com/company_docs/{filename}"

@app.route('/upload_video', methods=['GET','POST'])
def upload_video(): 
    if request.files:
        video = request.files['video']
        if video.filename != '':
            upload_folder = 'uploads'
            os.makedirs(upload_folder, exist_ok=True)
            video_path = os.path.join(upload_folder, video.filename)
            video.save(video_path)
            return jsonify({'result': 'nothing', 'video_path': video_path})
    return jsonify({'error': 'لم يتم إرفاق ملف أو الملف المرفق تالف'})

@app.route('/submit_post', methods=['POST'])
@login_required
def submit_post():
    user_email = current_user.get_id()
    if not user_email:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح بها', 'danger')
        return redirect(url_for('newsoutlet_login'))

    user_ref = db.reference('newsoutlet').order_by_child('email').equal_to(user_email).get()
    if not user_ref:
        flash('<i class="fas fa-times-circle me-3"></i> المستخدم غير موجود', 'danger')
        return redirect(url_for('newsoutlet_login'))
    username = list(user_ref.values())[0].get('username')

    title = request.form['title']
    body = request.form['body']
    media = request.files.get('media')

    bucket = storage.bucket()

    media_url = None 
    if media and media.filename:
        filename = secure_filename(media.filename)
        blob = bucket.blob(f'posts/{username}/{filename}')
        content_type = media.content_type
        if not content_type:
            extension = filename.split('.')[-1].lower()
            if extension == 'mp4':
                content_type = 'video/mp4'
            elif extension == 'webm':
                content_type = 'video/webm'
            elif extension == 'ogg':
                content_type = 'video/ogg'
            elif extension == 'mov':
                content_type = 'video/quicktime'
            else:
                content_type = 'application/octet-stream'

        blob.upload_from_file(media.stream, content_type=content_type)
        blob.make_public()
        media_url = blob.public_url

    timestamp = datetime.now()
    formatted_timestamp = timestamp.strftime("%b %d, %Y %I:%M%p")
    formatted_comment = ""
    post_data = {
        'title': title,
        'body': body,
        'media_url': media_url,
        'author': username,
        'author_email': user_email,
        'timestamp': formatted_timestamp,
        'comment': formatted_comment,
        'likes': 0,  
        'liked_by': []  
      }
    

    post_ref= db.reference('posts').push(post_data)
    post_id = post_ref.key
    
    notifications = list(user_ref.values())[0].get('notifications', [])
    if notifications:
        for notification in notifications:
            member_email = notification.get('member_id')
            if member_email:
                member_email = member_email.lower()
                notification_id = str(uuid.uuid4()) 

                notification_data = {
                    'member_id': member_email,
                    'newsoutlet': username,
                    'post_title': title,
                    'post_content': body,
                    'timestamp': formatted_timestamp,
                    'notification_id': notification_id,
                    'post_id': post_id 
                }

                
                db.reference('notifications').push(notification_data)

                print(f"أرسلنا الإشعار إلى: {member_email}")  
            else:
                print("Member email missing in notification")  
    else:
        print("لم تفعل الإشعارات لنشرات هذه المنصة الإخبارية")  

    flash('<i class="fas fa-check-circle me-3" style="color: green;"></i> تم إضافة النشرة بنجاح', 'success')
    return redirect(request.referrer)

@app.route('/delete_post/<string:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    user_email = current_user.get_id()
    if not user_email:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح بها', 'danger')
        return redirect(url_for('newsoutlet_login'))

    # Delete post
    post_ref = db.reference(f'posts/{post_id}')
    post_ref.delete()

    # Delete all related notifications
    notifications_ref = db.reference('notifications')
    related_notifications = notifications_ref.order_by_child('post_id').equal_to(post_id).get()
    if related_notifications:
        for notification_id in related_notifications.keys():
            notifications_ref.child(notification_id).delete()

    flash('<i class="fas fa-check-circle me-3" style="color: green;"></i> تم حذف النشرة بنجاح', 'success')

    referrer = request.referrer
    if 'post' in referrer:
        return redirect(url_for('home'))
    elif 'profile' in referrer:
        return redirect(url_for('profile', username=current_user.username))
    
    return redirect(url_for('home'))

@app.route('/admin/logout')
@app.route('/logout')
def logout():
    session.clear()
    logout_user()
    flash('<i class="fas fa-check-circle me-3" style="color: green;"></i> تم تسجيل خروجك بنجاح', 'success')
    return redirect(url_for('clear_session_storage'))
    
@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    form = ResetPasswordRequestForm()
    return render_template('reset_password_request.html', form=form)

@app.route('/GP1routeRelease1', methods=['GET', 'POST'])
def adminlogin():
    form = LoginForm()
    if form.validate_on_submit():
        api_key = "AIzaSyAXgzwyWNcfI-QSO_IbBVx9luHc9zOUzeY"
        request_payload = {
            "email": form.email.data,
            "password": form.password.data,
            "returnSecureToken": True
        }
        try:
            response = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}", json=request_payload)
            response.raise_for_status()
            user_info = response.json()
            email = form.email.data
            user_role = determine_user_role(email)
            session['logged_in'] = True
            session['role'] = user_role 
            if user_role == 'admin':
                flash('<i class="fas fa-check-circle me-3" style="color: green;"></i> تم تسجيل دخولك كمسؤول', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('<i class="fas fa-times-circle me-3"></i> فشل تسجيل دخولك، راجع بريدك الإلكتروني وكلمة المرور', 'danger')

        except requests.exceptions.HTTPError as e:
            error_json = e.response.json()
            error_message = error_json.get('error', {}).get('message', 'مشكلة غير معروفة')
            flash(f'<i class="fas fa-times-circle me-3"></i> فشل تسجيل دخولك، راجع بريدك الإلكتروني وكلمة المرور', 'danger')
    return render_template('adsecretlogin.html', title='تسجيل الدخول', form=form)

@app.route('/dashboard')
def admin_dashboard():
    if 'logged_in' in session and session['role'] == 'admin':
        ref = db.reference('registration_requests')
        requests = ref.order_by_child('status').equal_to('under review').get()

        for key, request in requests.items():
            if 'company_docs_url' in request and request['company_docs_url'].startswith('gs://'):
                gs_url = request['company_docs_url']
                https_url = gs_url.replace('gs://', 'https://storage.googleapis.com/', 1)
                request['company_docs_url'] = https_url
        
        return render_template('admin_dashboard.html', requests=requests)
    else:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح، الرجاء تسجيل الدخول كمسؤول', 'danger')
        return redirect(url_for('member_login'))
    
@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow_newsoutlet(username):
    useremail = request.form.get('useremail')  
    newsoutlet_data = firebase_database.child('newsoutlet').order_by_child('email').equal_to(useremail).get()

    if newsoutlet_data:
        newsoutlet_key, newsoutlet_info = list(newsoutlet_data.items())[0]
        member_id = session['user_email']  

        
        if member_id == useremail:
            return jsonify({'success': False, 'message': 'لايمكنك متابعة حسابك الشحصي'})

        current_followers = newsoutlet_info.get('followers', [])

        
        if not isinstance(current_followers, list):
            current_followers = []

        
        is_already_following = any(follow.get('member_id') == member_id for follow in current_followers)
        if is_already_following:
            return jsonify({'success': False, 'message': 'انت تتابع هذه المنصة بالفعل'})

        follow_data = {
            'member_id': member_id,
            'newsoutlet_id': useremail
        }
        firebase_database.child('follows').push(follow_data)
        
        current_followers.append({'member_id': member_id})
        firebase_database.child('newsoutlet').child(newsoutlet_key).update({'followers': current_followers})

        
        follower_usernames = set()  
        for follower in current_followers:
            member_email = follower['member_id']

            if member_email == useremail:
                continue

            
            user_data = firebase_database.child('members').order_by_child('email').equal_to(member_email).get()
            if user_data:
                user_key, user_info = list(user_data.items())[0]
                follower_usernames.add(user_info.get('username'))

            
            newsoutlet_data = firebase_database.child('newsoutlet').order_by_child('email').equal_to(member_email).get()
            if newsoutlet_data:
                newsoutlet_key, newsoutlet_info = list(newsoutlet_data.items())[0]
                follower_usernames.add(newsoutlet_info.get('username'))

        return jsonify({
            'success': True,
            'follower_count': len(current_followers),
            'followers': list(follower_usernames)  
        })

    else:
        return jsonify({'success': False, 'message': 'News Outlet not found'})

@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow_newsoutlet(username):
    useremail = request.form.get('useremail')
    newsoutlet_data = firebase_database.child('newsoutlet').order_by_child('email').equal_to(useremail).get()

    if newsoutlet_data:
        newsoutlet_key, newsoutlet_info = list(newsoutlet_data.items())[0]
        member_id = session['user_email']

        current_followers = newsoutlet_info.get('followers', [])
        if current_followers is None:
            current_followers = []  

        current_followers = [follow for follow in current_followers if follow.get('member_id') != member_id]

        
        firebase_database.child('newsoutlet').child(newsoutlet_key).update({'followers': current_followers})

        
        follow_entries = firebase_database.child('follows').order_by_child('member_id').equal_to(member_id).get()
        for key, entry in follow_entries.items():
            if entry.get('newsoutlet_id') == useremail:
                firebase_database.child('follows').child(key).delete()

   
        unnotify_newsoutlet(member_id)

    
        follower_usernames = []
        for follow in current_followers:
            follower_email = follow.get('member_id')
            member_data = firebase_database.child('members').order_by_child('email').equal_to(follower_email).get()
            if member_data:
                member_key, member_info = list(member_data.items())[0]
                follower_usernames.append(member_info.get('username'))

        for follow in current_followers:
            follower_email = follow.get('member_id')
            newsoutlet_data = firebase_database.child('newsoutlet').order_by_child('email').equal_to(follower_email).get()
            if newsoutlet_data:
                newsoutlet_key, newsoutlet_info = list(newsoutlet_data.items())[0]
                follower_usernames.append(newsoutlet_info.get('username'))


        return jsonify({
            'success': True,
            'follower_count': len(current_followers),
            'followers': follower_usernames
        })

    else:
        return jsonify({'success': False, 'message': 'لم يتم إيجاد صفحة المنصة'})

@app.route('/notify/<username>', methods=['POST'])
@login_required
def notify_newsoutlet(username):
    useremail = request.form.get('useremail')
    newsoutlet_data = firebase_database.child('newsoutlet').order_by_child('email').equal_to(useremail).get()

    if newsoutlet_data:
        newsoutlet_key, newsoutlet_info = list(newsoutlet_data.items())[0]
        member_id = session['user_email']
        current_notifications = newsoutlet_info.get('notifications', [])

        if isinstance(current_notifications, dict):
            current_notifications = [current_notifications]

        if isinstance(current_notifications, list):
            converted_notifications = []
            for notification in current_notifications:
                if isinstance(notification, str):
                    converted_notifications.append({'member_id': notification})
                elif isinstance(notification, dict):
                    converted_notifications.append(notification)
                else:
                    print(f"حصل خطأ في طريقة كتابة الإشعار: {notification}")

            current_notifications = converted_notifications

        is_already_notified = any(notification.get('member_id') == member_id for notification in current_notifications)

        if is_already_notified:
            return jsonify({'success': False, 'message': 'أنت مسجل بالفعل في إشعارات هذه المنصة الإعلامية'})
        else:
            current_notifications.append({'member_id': member_id})
            firebase_database.child('newsoutlet').child(newsoutlet_key).update({'notifications': current_notifications})
            return jsonify({'success': True, 'message': 'تم تفعيل الإشعارات', 'notification_count': len(current_notifications)})
    else:
        return jsonify({'success': False, 'message': 'لم نستطع إيجاد المنصة الإعلامية'})

@app.route('/unnotify/<username>', methods=['POST'])
@login_required
def unnotify_newsoutlet(username):
    useremail = request.form.get('useremail')
    newsoutlet_data = firebase_database.child('newsoutlet').order_by_child('email').equal_to(useremail).get()

    if newsoutlet_data:
        newsoutlet_key, newsoutlet_info = list(newsoutlet_data.items())[0]
        member_id = session['user_email']
        current_notifications = newsoutlet_info.get('notifications', [])

        if isinstance(current_notifications, int):
            current_notifications = [{'member_id': 'placeholder'} for _ in range(current_notifications)]

        current_notifications = [notification for notification in current_notifications if notification.get('member_id') != member_id]
        firebase_database.child('newsoutlet').child(newsoutlet_key).update({'notifications': current_notifications})

        notification_entries = firebase_database.child('notifications').order_by_child('member_id').equal_to(member_id).get()
        for key, entry in notification_entries.items():
            if entry.get('newsoutlet_id') == useremail:
                firebase_database.child('notifications').child(key).delete()
        return jsonify({'success': True, 'message': 'تم إلغاء الاشعارات', 'notification_count': len(current_notifications)})
    else:
        return jsonify({'success': False, 'message': 'لم نستطع إيجاد المنصة الإعلامية'})

def fetch_notifications(user_email):
    notifications_ref = db.reference('notifications').order_by_child('member_id').equal_to(user_email.lower()).get()
    all_notifications = firebase_database.child('notifications').order_by_child('member_id').equal_to(user_email).get()

    notifications = []
    unread_count = 0  
    user_email = session['user_email']

    if notifications_ref:
        for notification_key, notification_data in all_notifications.items():
            post_id = notification_data.get('post_id')  
            post_exists = db.reference('posts').child(post_id).get() is not None

            if post_exists:
                is_read = notification_data.get('is_read', False)
                notifications.append({
                    'notification_key': notification_key,  
                    'post_title': notification_data.get('post_title'),
                    'newsoutlet': notification_data.get('newsoutlet'),
                    'timestamp': notification_data.get('timestamp'),
                    'is_read': is_read,
                    'post_id': post_id  
                })
                
                if not is_read:
                    unread_count += 1

    notifications.reverse()
    return notifications, unread_count

@app.route('/fetch_notifications', methods=['GET'])
def fetch_notifications_route():
    user_email = session.get('user_email')
    if user_email:
        notifications, unread_count = fetch_notifications(user_email)
        return jsonify({'success': True, 'notifications': notifications, 'unread_count': unread_count})
    else:
        return jsonify({'success': False, 'message': 'لم تقم بتسجيل الدخول'})

@app.route('/notifications/mark_all_read', methods=['POST'])
@login_required
def mark_all_notifications_as_read():
    user_email = session.get('user_email')

    if not user_email:
        return jsonify({'success': False, 'message': 'لم تقم بتسجيل الدخول'}), 401

    
    notifications_ref = firebase_database.child('notifications').order_by_child('member_id').equal_to(user_email).get()

    if notifications_ref:
        for notification_key, notification_data in notifications_ref.items():
            if not notification_data.get('is_read', False):
                
                firebase_database.child('notifications').child(notification_key).update({'is_read': True})

        return jsonify({'success': True, 'message': 'تم تحديد جميع الإشعارات كمقروه'}), 200
    
    return jsonify({'success': False, 'message': 'No notifications found'}), 404

@app.route('/notification/delete/<notification_key>', methods=['POST'])
@login_required
def delete_notification(notification_key):
    user_email = session['user_email']
    
    notification_ref = firebase_database.child('notifications').child(notification_key).get()
    
    if notification_ref and notification_ref.get('member_id') == user_email:
        firebase_database.child('notifications').child(notification_key).delete()
        return jsonify({'success': True, 'message': 'تم حذف الإشعار بنجاح'})
    
    return jsonify({'success': False, 'message': 'لم يتم إيجاد الإشعار'})

@app.route('/post/<string:post_id>')
def post(post_id):
    username = session.get('user_email')
    posts = fetch_posts()  
    post = next((p for p in posts if p['post_id'] == post_id), None)  

    if not post:
        abort(404)  

    return render_template('post.html', post=post, username=username)

@app.context_processor
def inject_notifications():
    if 'user_email' in session:  
        notifications, unread_count = fetch_notifications(session['user_email']) 
    else:
        notifications = [] 
        unread_count = 0  
    return {'notifications': notifications, 'unread_count': unread_count}

@app.route('/post/<string:post_id>/add_comment', methods=['POST'])
@login_required
def add_comment(post_id):
    user_email = current_user.get_id()

    if not user_email:
        flash('الوصول غير مصرح به', 'danger')
        return redirect(url_for('newsoutlet_login'))

    user_ref = db.reference('members').order_by_child('email').equal_to(user_email).get()

    if not user_ref:
        user_ref = db.reference('newsoutlet').order_by_child('email').equal_to(user_email).get()

    if not user_ref:
        flash('لم يتم العثور على المستخدم', 'danger')
        return redirect(url_for('newsoutlet_login'))

    username = list(user_ref.values())[0].get('username')
    comment_body = request.form['comment']

    comment_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%b %d, %Y %I:%M%p")
    formatted_replies = ""
    comment_data = {
        'comment_id': comment_id,
        'author': username,
        'author_email': user_email,
        'body': comment_body,
        'timestamp': timestamp,
        'replies': formatted_replies
    }

    db.reference(f'posts/{post_id}/comment').child(comment_id).set(comment_data)

    flash('تمت إضافة التعليق بنجاح', 'success')
    return redirect(url_for('post', post_id=post_id))

@app.route('/post/<string:post_id>/reply/<string:comment_id>', defaults={'parent_reply_id': None}, methods=['POST'])
@app.route('/post/<string:post_id>/reply/<string:comment_id>/<string:parent_reply_id>', methods=['POST'])
@login_required
def reply_comment(post_id, comment_id, parent_reply_id):
    user_email = current_user.get_id()
    if not user_email:
        flash('الوصول غير مصرح به', 'danger')
        return redirect(url_for('newsoutlet_login'))

    user_ref = db.reference('members').order_by_child('email').equal_to(user_email).get()
    if not user_ref:
        user_ref = db.reference('newsoutlet').order_by_child('email').equal_to(user_email).get()

    if not user_ref:
        flash('لم يتم العثور على المستخدم', 'danger')
        return redirect(url_for('newsoutlet_login'))

    username = list(user_ref.values())[0].get('username')
    reply_body = request.form['reply']

    reply_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%b %d, %Y %I:%M%p")

    reply_data = {
        'reply_id': reply_id,
        'author': username,
        'author_email': user_email,
        'body': reply_body,
        'timestamp': timestamp,
        'parent_commentId': comment_id,
        'parent_replyId': parent_reply_id
    }

    db.reference(f'posts/{post_id}/comment/{comment_id}/replies').child(reply_id).set(reply_data)

    flash('تمت إضافة الرد بنجاح', 'success')
    return redirect(url_for('post', post_id=post_id))

@app.route('/post/<string:post_id>/comment/<string:comment_id>', methods=['POST'])
@login_required
def delete_comment(post_id, comment_id):
    user_email = current_user.get_id()
    if not user_email:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح بها', 'danger')
        return redirect(url_for('newsoutlet_login'))

    comment_ref = db.reference(f'posts/{post_id}/comment/{comment_id}')
    comment_data = comment_ref.get()

    if not comment_data:
        flash('<i class="fas fa-times-circle me-3"></i> التعليق غير موجود', 'danger')
        return redirect(url_for('post', post_id=post_id))

    post_ref = db.reference(f'posts/{post_id}')
    post_data = post_ref.get()

    if not post_data:
        flash('<i class="fas fa-times-circle me-3"></i> النشرة غير موجودة', 'danger')
        return redirect(url_for('home'))

    if comment_data['author_email'] != user_email and post_data['author_email'] != user_email:
        flash('<i class="fas fa-times-circle me-3"></i> ليس لديك إذن لحذف هذا التعليق', 'danger')
        return redirect(url_for('post', post_id=post_id))

    comment_ref.delete()
    flash('<i class="fas fa-check-circle me-3" style="color: green;"></i> تم حذف التعليق بنجاح', 'success')

    return redirect(url_for('post', post_id=post_id))

@app.route('/post/<string:post_id>/reply/<string:comment_id>/delete/<string:reply_id>', methods=['POST'])
@login_required
def delete_reply(post_id, comment_id, reply_id):
    user_email = current_user.get_id()

    if not user_email:
        flash('<i class="fas fa-times-circle me-3"></i> محاولة دخول غير مصرح بها', 'danger')
        return redirect(url_for('newsoutlet_login'))

    reply_ref = db.reference(f'posts/{post_id}/comment/{comment_id}/replies/{reply_id}')
    reply_data = reply_ref.get()

    if not reply_data:
        flash('<i class="fas fa-times-circle me-3"></i> الرد غير موجود', 'danger')
        return redirect(url_for('post', post_id=post_id))

    post_ref = db.reference(f'posts/{post_id}')
    post_data = post_ref.get()

    if not post_data:
        flash('<i class="fas fa-times-circle me-3"></i> النشرة غير موجودة', 'danger')
        return redirect(url_for('home'))

    if reply_data['author_email'] != user_email and post_data['author_email'] != user_email:
        flash('<i class="fas fa-times-circle me-3"></i> ليس لديك إذن لحذف هذا الرد', 'danger')
        return redirect(url_for('post', post_id=post_id))

    reply_ref.delete()
    flash('<i class="fas fa-check-circle me-3" style="color: green;"></i> تم حذف الرد بنجاح', 'success')

    return redirect(url_for('post', post_id=post_id))

@app.route('/like_post/<post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    user_email = current_user.get_id()
    if not user_email:
        return jsonify({'success': False, 'message': 'دخول غير مصرح به'}), 403

    post_ref = db.reference(f'posts/{post_id}')
    post_data = post_ref.get()
    if not post_data:
        return jsonify({'success': False, 'message': 'لم يتم إيجاد النشرة'}), 404

    likes = post_data.get('likes', 0)
    liked_by = post_data.get('liked_by', [])

    if user_email in liked_by:
        liked_by.remove(user_email)
        likes -= 1
    else:
        liked_by.append(user_email)
        likes += 1
    post_ref.update({
        'likes': likes,
        'liked_by': liked_by
    })

    return jsonify({'success': True, 'likes': likes})

@app.route('/unlike_post/<post_id>', methods=['POST'])
@login_required
def unlike_post(post_id):
    user_email = current_user.get_id()  

    if not user_email:
        return jsonify({'success': False, 'message': 'دخول غير مصرح به'}), 403

    post_ref = db.reference(f'posts/{post_id}')
    post_data = post_ref.get()

    if not post_data:
        return jsonify({'success': False, 'message': 'لم يتم إيجاد النشرة'}), 404


    liked_by = post_data.get('liked_by', [])

    if user_email not in liked_by:
        return jsonify({'success': False, 'message': 'لم تقم بوضع علامة الإعجاب لهذه النشرة'}), 400

    liked_by.remove(user_email)
    likes = max(post_data.get('likes', 0) - 1, 0)  
    post_ref.update({
        'likes': likes,
        'liked_by': liked_by
    })
    return jsonify({'success': True, 'likes': likes})

@app.route('/clear_session_storage')
def clear_session_storage():
    return '''
    <script>
        sessionStorage.clear();
        window.location.href = '/';
    </script>
    '''

@app.route('/liked_posts')
@login_required
def liked_posts():
    user_liked_posts = fetch_liked_posts(current_user.get_id())  
    
    return render_template('liked_posts.html', liked_posts=user_liked_posts)
