import os
import textwrap
import unicodedata
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
import smtplib

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'

# CONFIG MYSQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root123'
app.config['MYSQL_DB'] = 'asesoria_juridica'

mysql = MySQL(app)

BASE_DIR = Path(__file__).resolve().parent
OUTBOX_DIR = BASE_DIR / 'emails_outbox'
PDF_DIR = BASE_DIR / 'static' / 'case_pdfs'

ESPECIALIDADES = {
    'familia': [
        'divorcio', 'alimentos', 'pension', 'custodia', 'visitas', 'tuicion',
        'familia', 'conyuge', 'matrimonio', 'hijos'
    ],
    'laboral': [
        'despido', 'finiquito', 'sueldo', 'remuneracion', 'laboral',
        'trabajo', 'empleador', 'contrato', 'cotizaciones', 'acoso'
    ],
    'civil': [
        'contrato', 'deuda', 'arrendamiento', 'arriendo', 'indemnizacion',
        'civil', 'propiedad', 'incumplimiento', 'cobranza'
    ],
    'penal': [
        'delito', 'denuncia', 'querella', 'robo', 'estafa', 'amenaza',
        'lesiones', 'penal', 'detencion', 'violencia', "hurto"
    ],
    'comercial': [
        'empresa', 'sociedad', 'factura', 'comercial', 'marca', 'proveedor',
        'cliente', 'quiebra', 'startup', 'negocio'
    ],
    'inmobiliario': [
        'inmueble', 'casa', 'departamento', 'compraventa', 'hipoteca',
        'condominio', 'terreno', 'inmobiliario', 'escritura'
    ],
    'migratorio': [
        'visa', 'residencia', 'extranjero', 'migracion', 'permiso',
        'nacionalidad', 'expulsion'
    ],
}


def load_env_file():
    env_path = BASE_DIR / '.env'
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()


def login_required():
    return 'user_id' in session


def owner_required():
    return login_required() and session.get('tipo') == 'dueno'


def hash_password(password):
    return generate_password_hash(password)


def verify_password(stored_password, provided_password):
    if not stored_password:
        return False

    if stored_password == provided_password:
        return True

    try:
        return check_password_hash(stored_password, provided_password)
    except ValueError:
        return False


def normalizar_texto(texto):
    texto = texto or ''
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return texto.lower()


def detect_column(table_name, column_name):
    cur = mysql.connection.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s AND column_name = %s
        """,
        (app.config['MYSQL_DB'], table_name, column_name)
    )
    return cur.fetchone()[0] > 0


def table_exists(table_name):
    cur = mysql.connection.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        """,
        (app.config['MYSQL_DB'], table_name)
    )
    return cur.fetchone()[0] > 0


def fetchone_dict(query, params=()):
    cur = mysql.connection.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    if row is None:
        return None
    columns = [desc[0] for desc in cur.description]
    return dict(zip(columns, row))


def fetchall_dict(query, params=()):
    cur = mysql.connection.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in rows]


def get_abogados():
    return fetchall_dict(
        """
        SELECT
            id,
            nombre,
            email,
            COALESCE(especialidades, '') AS especialidades,
            COALESCE(foto_url, '') AS foto_url,
            COALESCE(bio, '') AS bio,
            COALESCE(universidad, '') AS universidad,
            COALESCE(experiencia, '') AS experiencia
        FROM usuarios
        WHERE tipo = %s
        ORDER BY nombre
        """,
        ('abogado',)
    )


def get_consulta_por_id(consulta_id):
    return fetchone_dict(
        """
        SELECT
            c.id,
            c.titulo,
            c.descripcion,
            c.usuario_id,
            c.abogado_id,
            c.estado,
            COALESCE(c.especialidad_detectada, '') AS especialidad_detectada,
            COALESCE(c.pdf_respaldo, '') AS pdf_respaldo,
            cliente.nombre AS cliente_nombre,
            cliente.email AS cliente_email,
            COALESCE(abogado.nombre, '') AS abogado_nombre,
            COALESCE(abogado.email, '') AS abogado_email
        FROM consultas c
        JOIN usuarios cliente ON cliente.id = c.usuario_id
        LEFT JOIN usuarios abogado ON abogado.id = c.abogado_id
        WHERE c.id = %s
        """,
        (consulta_id,)
    )


def usuario_puede_ver_consulta(consulta):
    if not consulta or not login_required():
        return False
    if session.get('tipo') == 'dueno':
        return True
    if session.get('tipo') == 'cliente' and consulta['usuario_id'] == session['user_id']:
        return True
    if session.get('tipo') == 'abogado' and consulta['abogado_id'] == session['user_id']:
        return True
    return False


def detectar_especialidad(titulo, descripcion):
    titulo_normalizado = normalizar_texto(titulo)
    descripcion_normalizada = normalizar_texto(descripcion)
    puntajes = {}

    for especialidad, palabras in ESPECIALIDADES.items():
        puntaje_titulo = sum(3 for palabra in palabras if palabra in titulo_normalizado)
        puntaje_descripcion = sum(1 for palabra in palabras if palabra in descripcion_normalizada)
        puntajes[especialidad] = puntaje_titulo + puntaje_descripcion

    especialidad, puntaje = max(puntajes.items(), key=lambda item: item[1])
    return especialidad if puntaje > 0 else None


def elegir_abogado_para_especialidad(especialidad):
    if not especialidad:
        return None

    abogados = fetchall_dict(
        """
        SELECT id, COALESCE(especialidades, '') AS especialidades
        FROM usuarios
        WHERE tipo = %s
        """,
        ('abogado',)
    )

    mejores_coincidencias = []
    for abogado in abogados:
        especialidades = normalizar_texto(abogado['especialidades'])
        if especialidad in especialidades:
            carga = fetchone_dict(
                "SELECT COUNT(*) AS total FROM consultas WHERE abogado_id = %s",
                (abogado['id'],)
            )
            mejores_coincidencias.append((carga['total'], abogado['id']))

    if not mejores_coincidencias:
        return None

    mejores_coincidencias.sort()
    return mejores_coincidencias[0][1]


def escape_pdf_text(texto):
    return (
        texto.replace('\\', '\\\\')
        .replace('(', '\\(')
        .replace(')', '\\)')
    )


def pdf_line(x1, y1, x2, y2, width=1):
    return f'{width} w {x1} {y1} m {x2} {y2} l S'


def pdf_rect(x, y, width, height, fill_rgb=None, stroke_rgb=None, line_width=1):
    commands = []
    if fill_rgb:
        commands.append(f'{fill_rgb[0]} {fill_rgb[1]} {fill_rgb[2]} rg')
    if stroke_rgb:
        commands.append(f'{stroke_rgb[0]} {stroke_rgb[1]} {stroke_rgb[2]} RG')
        commands.append(f'{line_width} w')

    operator = 'B' if fill_rgb and stroke_rgb else 'f' if fill_rgb else 'S'
    commands.append(f'{x} {y} {width} {height} re {operator}')
    return '\n'.join(commands)


def pdf_text_block(lines, x, y, font='F1', size=11, leading=14, color=(0.18, 0.22, 0.2)):
    commands = [
        'BT',
        f'/{font} {size} Tf',
        f'{color[0]} {color[1]} {color[2]} rg',
        f'{x} {y} Td',
        f'{leading} TL',
    ]
    for line in lines:
        commands.append(f'({escape_pdf_text(line)}) Tj')
        commands.append('T*')
    commands.append('ET')
    return '\n'.join(commands)


def wrap_pdf_text(texto, width):
    return textwrap.wrap(texto or '', width=width) or ['Sin descripcion']


def generate_case_pdf(consulta):
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    filename = f'consulta_{consulta["id"]}.pdf'
    pdf_path = PDF_DIR / filename

    title_lines = wrap_pdf_text(consulta['titulo'], 52)
    description_lines = wrap_pdf_text(consulta['descripcion'], 88)

    content_lines = [
        pdf_rect(0, 770, 595, 72, fill_rgb=(0.09, 0.25, 0.2)),
        pdf_rect(40, 620, 515, 120, fill_rgb=(0.97, 0.95, 0.9), stroke_rgb=(0.78, 0.69, 0.52), line_width=1),
        pdf_rect(40, 80, 515, 520, fill_rgb=(1, 1, 1), stroke_rgb=(0.88, 0.86, 0.8), line_width=1),
        pdf_line(40, 602, 555, 602, width=1),
        pdf_text_block(['LEXORA LEGAL'], 44, 815, font='F2', size=20, leading=22, color=(1, 1, 1)),
        pdf_text_block(['Respaldo formal de consulta juridica'], 44, 792, font='F1', size=10, leading=12, color=(0.9, 0.93, 0.91)),
        pdf_text_block(title_lines, 44, 742, font='F2', size=18, leading=20, color=(0.12, 0.17, 0.14)),
        pdf_text_block([f'Caso #{consulta["id"]}'], 455, 815, font='F1', size=10, leading=12, color=(0.94, 0.86, 0.7)),
        pdf_text_block(
            [
                f'Cliente: {consulta["cliente_nombre"]}',
                f'Abogado asignado: {consulta["abogado_nombre"] or "Sin asignar"}',
                f'Area detectada: {consulta["especialidad_detectada"] or "Revision manual"}',
                f'Estado actual: {consulta["estado"]}',
                f'Fecha de emision: {datetime.now().strftime("%d-%m-%Y %H:%M")}',
            ],
            58,
            715,
            font='F1',
            size=11,
            leading=17,
            color=(0.2, 0.24, 0.22)
        ),
        pdf_text_block(['Descripcion del caso'], 54, 575, font='F2', size=14, leading=16, color=(0.1, 0.24, 0.2)),
        pdf_text_block(description_lines, 54, 548, font='F1', size=11, leading=15, color=(0.18, 0.22, 0.2)),
        pdf_text_block(
            ['Documento generado automaticamente por Lexora Legal para seguimiento interno y respaldo del caso.'],
            54,
            110,
            font='F1',
            size=9,
            leading=11,
            color=(0.42, 0.46, 0.44)
        ),
    ]

    content = '\n'.join(content_lines).encode('latin-1', errors='replace')

    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>',
        f'<< /Length {len(content)} >>\nstream\n'.encode('latin-1') + content + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>',
    ]

    pdf = b'%PDF-1.4\n'
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f'{index} 0 obj\n'.encode('latin-1') + obj + b'\nendobj\n'

    xref_start = len(pdf)
    pdf += f'xref\n0 {len(objects) + 1}\n'.encode('latin-1')
    pdf += b'0000000000 65535 f \n'
    for offset in offsets[1:]:
        pdf += f'{offset:010} 00000 n \n'.encode('latin-1')
    pdf += (
        f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n'
        f'startxref\n{xref_start}\n%%EOF'
    ).encode('latin-1')

    pdf_path.write_bytes(pdf)
    return f'case_pdfs/{filename}'


def send_email_with_fallback(destinatario, asunto, cuerpo, attachment_paths=None):
    attachment_paths = attachment_paths or []
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_from = os.getenv('SMTP_FROM', smtp_user or 'no-reply@lexora.local')

    message = EmailMessage()
    message['Subject'] = asunto
    message['From'] = smtp_from
    message['To'] = destinatario
    message.set_content(cuerpo)

    for attachment_path in attachment_paths:
        file_path = BASE_DIR / attachment_path
        if file_path.exists():
            message.add_attachment(
                file_path.read_bytes(),
                maintype='application',
                subtype='pdf',
                filename=file_path.name
            )

    try:
        if not all([smtp_host, smtp_user, smtp_password]):
            raise RuntimeError('SMTP no configurado')

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
        return True
    except Exception:
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        outbox_file = OUTBOX_DIR / f'{timestamp}_{destinatario.replace("@", "_at_")}.eml'
        respaldo = [
            f'TO: {destinatario}',
            f'SUBJECT: {asunto}',
            '',
            cuerpo,
            '',
            'ATTACHMENTS:',
        ]
        respaldo.extend(attachment_paths)
        outbox_file.write_text('\n'.join(respaldo), encoding='utf-8')
        return False


def create_notification(user_id, titulo, mensaje, link=''):
    if not table_exists('notificaciones'):
        return
    cur = mysql.connection.cursor()
    cur.execute(
        """
        INSERT INTO notificaciones (usuario_id, titulo, mensaje, link, leida)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, titulo, mensaje, link, 0)
    )
    mysql.connection.commit()


def notify_case_created(consulta):
    attachment = [consulta['pdf_respaldo']] if consulta['pdf_respaldo'] else []
    create_notification(
        consulta['usuario_id'],
        'Solicitud creada',
        f'Se registro tu solicitud "{consulta["titulo"]}".',
        f'/consultas/{consulta["id"]}/chat'
    )
    send_email_with_fallback(
        consulta['cliente_email'],
        f'Confirmacion de solicitud #{consulta["id"]}',
        (
            f'Tu solicitud fue creada correctamente.\n\n'
            f'Titulo: {consulta["titulo"]}\n'
            f'Area detectada: {consulta["especialidad_detectada"] or "Revision manual"}\n'
            f'Estado: {consulta["estado"]}\n'
        ),
        attachment
    )


def notify_assignment(consulta, automatico=False):
    if not consulta['abogado_id']:
        return

    suffix = 'automaticamente' if automatico else 'manualmente'
    attachment = [consulta['pdf_respaldo']] if consulta['pdf_respaldo'] else []

    create_notification(
        consulta['usuario_id'],
        'Abogado asignado',
        f'Se asigno {suffix} a {consulta["abogado_nombre"]} en tu caso "{consulta["titulo"]}".',
        f'/consultas/{consulta["id"]}/chat'
    )
    create_notification(
        consulta['abogado_id'],
        'Nuevo caso asignado',
        f'Recibiste el caso "{consulta["titulo"]}" del cliente {consulta["cliente_nombre"]}.',
        f'/consultas/{consulta["id"]}/chat'
    )

    send_email_with_fallback(
        consulta['cliente_email'],
        f'Abogado asignado a tu caso #{consulta["id"]}',
        (
            f'Tu caso "{consulta["titulo"]}" fue asignado a {consulta["abogado_nombre"]}.\n'
            f'Area legal detectada: {consulta["especialidad_detectada"] or "Revision manual"}.\n'
        ),
        attachment
    )
    send_email_with_fallback(
        consulta['abogado_email'],
        f'Nuevo caso asignado #{consulta["id"]}',
        (
            f'Se te asigno el caso "{consulta["titulo"]}" del cliente {consulta["cliente_nombre"]}.\n'
            f'Revisa el respaldo PDF adjunto y responde por el chat del caso.\n'
        ),
        attachment
    )


@app.context_processor
def inject_globals():
    unread_count = 0
    if login_required() and table_exists('notificaciones'):
        row = fetchone_dict(
            "SELECT COUNT(*) AS total FROM notificaciones WHERE usuario_id = %s AND leida = 0",
            (session['user_id'],)
        )
        unread_count = row['total']

    return {
        'especialidades_disponibles': ESPECIALIDADES.keys(),
        'unread_notifications': unread_count,
        'sound_notifications_available': login_required(),
    }


@app.route('/')
def home():
    abogados = get_abogados()
    destacados = abogados[:3]
    return render_template('home.html', destacados=destacados)


@app.route('/abogados/publicos')
def abogados_publicos():
    abogados = get_abogados()
    return render_template('abogados_publicos.html', abogados=abogados)


@app.route('/crear_dueno', methods=['GET', 'POST'])
def crear_dueno():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM usuarios WHERE tipo = %s", ('dueno',))
    existe_dueno = cur.fetchone()[0] > 0

    if existe_dueno:
        flash('Ya existe un dueno de bufete. Inicia sesion con esa cuenta.')
        return redirect('/login')

    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']

        cur.execute(
            "INSERT INTO usuarios (nombre, email, password, tipo) VALUES (%s, %s, %s, %s)",
            (nombre, email, hash_password(password), 'dueno')
        )
        mysql.connection.commit()
        flash('Dueno creado correctamente. Ahora puedes iniciar sesion.')
        return redirect('/login')

    return render_template('crear_dueno.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        tipo = request.form['tipo']

        if tipo not in ('cliente', 'abogado'):
            return "Tipo de usuario no permitido"

        especialidades = ''
        foto_url = ''
        bio = ''
        universidad = ''
        experiencia = ''

        if tipo == 'abogado':
            especialidades = ', '.join(request.form.getlist('especialidades'))
            foto_url = request.form.get('foto_url', '')
            bio = request.form.get('bio', '')
            universidad = request.form.get('universidad', '')
            experiencia = request.form.get('experiencia', '')

        cur = mysql.connection.cursor()
        cur.execute(
            """
            INSERT INTO usuarios
                (nombre, email, password, tipo, especialidades, foto_url, bio, universidad, experiencia)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (nombre, email, hash_password(password), tipo, especialidades, foto_url, bio, universidad, experiencia)
        )
        mysql.connection.commit()
        flash('Usuario registrado correctamente')
        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM usuarios WHERE email=%s", (email,))
        user = cur.fetchone()

        if user and verify_password(user[3], password):
            session['user_id'] = user[0]
            session['tipo'] = user[4]
            session['nombre'] = user[1]

            if user[3] == password:
                cur.execute(
                    "UPDATE usuarios SET password = %s WHERE id = %s",
                    (hash_password(password), user[0])
                )
                mysql.connection.commit()

            return redirect('/dashboard')

        flash('Credenciales incorrectas')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if not login_required():
        return redirect('/login')

    return render_template('dashboard.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/abogados', methods=['GET', 'POST'])
def gestionar_abogados():
    if not owner_required():
        return redirect('/dashboard')

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        especialidades = ', '.join(request.form.getlist('especialidades'))
        foto_url = request.form.get('foto_url', '')
        bio = request.form.get('bio', '')
        universidad = request.form.get('universidad', '')
        experiencia = request.form.get('experiencia', '')

        cur.execute(
            """
            INSERT INTO usuarios
                (nombre, email, password, tipo, especialidades, foto_url, bio, universidad, experiencia)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (nombre, email, hash_password(password), 'abogado', especialidades, foto_url, bio, universidad, experiencia)
        )
        mysql.connection.commit()
        flash('Abogado creado correctamente con su perfil profesional')
        return redirect('/abogados')

    abogados = get_abogados()
    return render_template('abogados.html', abogados=abogados)


@app.route('/abogados/<int:abogado_id>/editar', methods=['GET', 'POST'])
def editar_abogado(abogado_id):
    if not owner_required():
        return redirect('/dashboard')

    abogado = fetchone_dict(
        """
        SELECT
            id, nombre, email, COALESCE(especialidades, '') AS especialidades,
            COALESCE(foto_url, '') AS foto_url, COALESCE(bio, '') AS bio,
            COALESCE(universidad, '') AS universidad, COALESCE(experiencia, '') AS experiencia
        FROM usuarios
        WHERE id = %s AND tipo = %s
        """,
        (abogado_id, 'abogado')
    )

    if abogado is None:
        flash('Abogado no encontrado')
        return redirect('/abogados')

    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form.get('password', '')
        especialidades = ', '.join(request.form.getlist('especialidades'))
        foto_url = request.form.get('foto_url', '')
        bio = request.form.get('bio', '')
        universidad = request.form.get('universidad', '')
        experiencia = request.form.get('experiencia', '')

        cur = mysql.connection.cursor()
        if password:
            cur.execute(
                """
                UPDATE usuarios
                SET nombre = %s, email = %s, password = %s, especialidades = %s,
                    foto_url = %s, bio = %s, universidad = %s, experiencia = %s
                WHERE id = %s
                """,
                (nombre, email, hash_password(password), especialidades, foto_url, bio, universidad, experiencia, abogado_id)
            )
        else:
            cur.execute(
                """
                UPDATE usuarios
                SET nombre = %s, email = %s, especialidades = %s,
                    foto_url = %s, bio = %s, universidad = %s, experiencia = %s
                WHERE id = %s
                """,
                (nombre, email, especialidades, foto_url, bio, universidad, experiencia, abogado_id)
            )
        mysql.connection.commit()
        flash('Perfil del abogado actualizado correctamente')
        return redirect('/abogados')

    return render_template('editar_abogado.html', abogado=abogado)


@app.route('/crear_consulta', methods=['GET', 'POST'])
def crear_consulta():
    if not login_required():
        return redirect('/login')

    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        usuario_id = session['user_id']
        especialidad_detectada = detectar_especialidad(titulo, descripcion)
        abogado_id = elegir_abogado_para_especialidad(especialidad_detectada)

        cur = mysql.connection.cursor()
        cur.execute(
            """
            INSERT INTO consultas
                (titulo, descripcion, usuario_id, abogado_id, especialidad_detectada, estado)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (titulo, descripcion, usuario_id, abogado_id, especialidad_detectada, 'pendiente')
        )
        mysql.connection.commit()
        consulta_id = cur.lastrowid

        consulta = get_consulta_por_id(consulta_id)
        pdf_respaldo = generate_case_pdf(consulta)

        cur.execute(
            "UPDATE consultas SET pdf_respaldo = %s WHERE id = %s",
            (pdf_respaldo, consulta_id)
        )
        mysql.connection.commit()

        consulta = get_consulta_por_id(consulta_id)
        notify_case_created(consulta)

        if abogado_id:
            notify_assignment(consulta, automatico=True)
            flash('Consulta creada y asignada automaticamente a un abogado especialista')
        else:
            flash('Consulta creada. Quedo pendiente de asignacion manual')

        return redirect('/consultas')

    return render_template('crear_consulta.html')


@app.route('/consultas')
def ver_consultas():
    if not login_required():
        return redirect('/login')

    tipo = session.get('tipo')
    consulta_base = """
        SELECT
            c.id,
            c.titulo,
            c.descripcion,
            cliente.nombre AS cliente,
            COALESCE(abogado.nombre, '') AS abogado,
            c.estado,
            c.abogado_id,
            COALESCE(c.especialidad_detectada, '') AS especialidad_detectada,
            COALESCE(c.pdf_respaldo, '') AS pdf_respaldo
        FROM consultas c
        JOIN usuarios cliente ON cliente.id = c.usuario_id
        LEFT JOIN usuarios abogado ON abogado.id = c.abogado_id
    """

    if tipo == 'cliente':
        consultas = fetchall_dict(
            consulta_base + " WHERE c.usuario_id = %s ORDER BY c.id DESC",
            (session['user_id'],)
        )
    elif tipo == 'abogado':
        consultas = fetchall_dict(
            consulta_base + " WHERE c.abogado_id = %s ORDER BY c.id DESC",
            (session['user_id'],)
        )
    elif tipo == 'dueno':
        consultas = fetchall_dict(consulta_base + " ORDER BY c.id DESC")
    else:
        return redirect('/dashboard')

    abogados = get_abogados() if tipo == 'dueno' else []
    return render_template('consultas.html', consultas=consultas, abogados=abogados)


@app.route('/consultas/<int:consulta_id>/asignar', methods=['POST'])
def asignar_consulta(consulta_id):
    if not owner_required():
        return redirect('/dashboard')

    abogado_id = request.form['abogado_id'] or None
    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE consultas SET abogado_id = %s WHERE id = %s",
        (abogado_id, consulta_id)
    )
    mysql.connection.commit()

    consulta = get_consulta_por_id(consulta_id)
    if consulta and abogado_id:
        notify_assignment(consulta, automatico=False)

    flash('Consulta asignada correctamente')
    return redirect('/consultas')


@app.route('/consultas/<int:consulta_id>/chat', methods=['GET', 'POST'])
def chat_consulta(consulta_id):
    if not login_required():
        return redirect('/login')

    consulta = get_consulta_por_id(consulta_id)
    if not usuario_puede_ver_consulta(consulta):
        flash('No tienes acceso a este chat')
        return redirect('/consultas')

    if request.method == 'POST':
        mensaje = request.form['mensaje'].strip()
        if mensaje:
            cur = mysql.connection.cursor()
            cur.execute(
                """
                INSERT INTO mensajes_chat (consulta_id, remitente_id, mensaje)
                VALUES (%s, %s, %s)
                """,
                (consulta_id, session['user_id'], mensaje)
            )
            mysql.connection.commit()

            destinatario_id = None
            destinatario_email = None
            if session['user_id'] == consulta['usuario_id'] and consulta['abogado_id']:
                destinatario_id = consulta['abogado_id']
                destinatario_email = consulta['abogado_email']
            elif session['user_id'] == consulta['abogado_id']:
                destinatario_id = consulta['usuario_id']
                destinatario_email = consulta['cliente_email']

            if destinatario_id:
                create_notification(
                    destinatario_id,
                    'Nuevo mensaje en el chat',
                    f'Hay un nuevo mensaje en el caso "{consulta["titulo"]}".',
                    f'/consultas/{consulta_id}/chat'
                )
            if destinatario_email:
                send_email_with_fallback(
                    destinatario_email,
                    f'Nuevo mensaje en el caso #{consulta_id}',
                    (
                        f'Se envio un nuevo mensaje en el caso "{consulta["titulo"]}".\n'
                        f'Ingresa al sistema para responder por el chat.\n'
                    )
                )

            flash('Mensaje enviado')
        return redirect(url_for('chat_consulta', consulta_id=consulta_id))

    mensajes = fetchall_dict(
        """
        SELECT
            m.id,
            m.mensaje,
            m.creado_en,
            u.id AS remitente_id,
            u.nombre AS remitente_nombre,
            u.tipo AS remitente_tipo
        FROM mensajes_chat m
        JOIN usuarios u ON u.id = m.remitente_id
        WHERE m.consulta_id = %s
        ORDER BY m.id ASC
        """,
        (consulta_id,)
    )
    return render_template('chat.html', consulta=consulta, mensajes=mensajes)


@app.route('/notificaciones')
def ver_notificaciones():
    if not login_required():
        return redirect('/login')

    if not table_exists('notificaciones'):
        flash('La tabla de notificaciones aun no existe. Ejecuta la migracion.')
        return redirect('/dashboard')

    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE notificaciones SET leida = 1 WHERE usuario_id = %s AND leida = 0",
        (session['user_id'],)
    )
    mysql.connection.commit()

    notificaciones = fetchall_dict(
        """
        SELECT id, titulo, mensaje, COALESCE(link, '') AS link, leida, creado_en
        FROM notificaciones
        WHERE usuario_id = %s
        ORDER BY id DESC
        """,
        (session['user_id'],)
    )
    return render_template('notificaciones.html', notificaciones=notificaciones)


if __name__ == '__main__':
    app.run(debug=True)
