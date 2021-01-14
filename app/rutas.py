from app import app, db
from flask import jsonify, request, render_template, make_response, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import Users
import uuid
import jwt
import datetime
from app.tokens import generate_confirmation_token, confirm_token
from flask_login import login_required, login_user, logout_user, current_user
from app.email import send_email
from formularios import LoginForm, RegistrationForm


@app.route('/')
def index():
    user = {'username': 'Miguel'}
    return render_template('index.html', title='Home', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = Users(public_id=str(uuid.uuid4()), personal_id=form.personal_id.data,
                     password=generate_password_hash(form.password.data), email=form.email.data, phone=form.phone.data,
                     kind=request.form.get('kind'), confirmed=False)
        db.session.add(user)
        db.session.commit()
        token = generate_confirmation_token(form.email.data)
        confirm_url = url_for('confirm_email', token=token, _external=True)
        html = render_template('activateuser.html', confirm_url=confirm_url)
        subject = "Please confirm your email"
        send_email(form.email.data, subject, html)

        flash('A confirmation email has been sent via email.', 'success')
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    dropdown_list = ['Hospital', 'Paciente']
    return render_template('register.html', title='Register', form=form, dropdown_list=dropdown_list)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(personal_id=form.personal_id.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Identificación o contraseña equivocados.')
            return redirect(url_for('login'))
        if not user.confirmed:
            flash('Por favor confirmar tu cuenta antes de iniciar sesión.')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)


@app.route('/otrologin')
def otrologin():
    data = request.get_json()
    auth = request.authorization

    if not auth or not auth.username or not auth.password:
        return make_response('No se pudo verificar', 401, {'WWW.Authentication': 'Basic realm: "login required"'})

    user = Users.query.filter_by(personal_id=data['personal_id']).first()
    if check_password_hash(user.password, data['password']):
        token = jwt.encode(
            {'public_id': user.public_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
            app.config['SECRET_KEY'])
        token_decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
        return jsonify({'token': token_decoded['public_id']})

    return make_response('No se pudo verificar', 401, {'WWW.Authentication': 'Basic realm: "login required"'})


@app.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
        return render_template('logout.html', title='Home')
    else:
        return render_template('notlogged.html', title='Home')



@app.route('/confirm/<token>')
@login_required
def confirm_email(token):
    try:
        email = confirm_token(token)
    except:
        flash('El link de confirmación es erróneo o ha expirado')
    user = Users.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash('Esta cuenta ya ha sido confirmada, por favor inicie sesión.')
    else:
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        flash('¡Has confirmado tu cuenta! ¡Gracias!')
    return redirect(url_for('index'))
