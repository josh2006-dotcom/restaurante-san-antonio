import os
from flask import (Flask, render_template, request,
                   redirect, url_for, session, flash, jsonify)
from werkzeug.utils import secure_filename
from database import get_connection

app = Flask(__name__)
app.secret_key = 'restaurante_san_antonio_clave_secreta_2024'

EXTENSIONES_IMG_PERMITIDAS = {'png', 'jpg', 'jpeg', 'webp'}

# ╔══════════════════════════════════════════════════════╗
# ║  INICIO — Menú público                               ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/')
def index():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT id_plato, nombre, precio, tipo, imagen FROM Plato WHERE disponible = TRUE ORDER BY tipo, nombre")
    platos = cur.fetchall()
    conn.close()
    return render_template('index.html', platos=platos)

# ╔══════════════════════════════════════════════════════╗
# ║  QUIÉNES SOMOS                                       ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/quienes_somos')
def quienes_somos():
    return render_template('quienes_somos.html')

# ╔══════════════════════════════════════════════════════╗
# ║  MENÚ SEMANAL — Público                              ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/menu_semanal')
def menu_semanal():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT dia, tipo, plato, semana, orden
        FROM Menu_Semanal
        ORDER BY
          CASE dia
            WHEN 'Lunes'     THEN 1
            WHEN 'Martes'    THEN 2
            WHEN 'Miércoles' THEN 3
            WHEN 'Jueves'    THEN 4
            WHEN 'Viernes'   THEN 5
            WHEN 'Sábado'    THEN 6
          END, tipo, orden
    """)
    filas = cur.fetchall()
    conn.close()

    menu = {}
    for dia, tipo, plato, semana, orden in filas:
        if dia not in menu:
            menu[dia] = {'entradas': [], 'segundos': [], 'bebidas': [], 'semana': semana}
        if tipo == 'entrada':
            menu[dia]['entradas'].append(plato)
        elif tipo == 'segundo':
            menu[dia]['segundos'].append(plato)
        elif tipo == 'bebida':
            menu[dia]['bebidas'].append(plato)

    return render_template('menu_semanal.html', menu=menu)

# ╔══════════════════════════════════════════════════════╗
# ║  MENÚ SEMANAL — Admin editar                         ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/admin/menu_semanal', methods=['GET', 'POST'])
def admin_menu_semanal():
    if not session.get('es_admin'):
        return redirect(url_for('admin_login'))

    conn = get_connection()
    cur  = conn.cursor()

    if request.method == 'POST':
        dias = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado']
        semana = request.form.get('semana', '')
        cur.execute("DELETE FROM Menu_Semanal")
        for dia in dias:
            i = 0
            while True:
                key = f'entrada_{dia}_{i}'
                if key not in request.form:
                    break
                valor = request.form.get(key, '').strip()
                if valor:
                    cur.execute("""
                        INSERT INTO Menu_Semanal (dia, tipo, plato, semana, orden)
                        VALUES (%s, 'entrada', %s, %s, %s)
                    """, (dia, valor, semana, i))
                i += 1
            i = 0
            while True:
                key = f'segundo_{dia}_{i}'
                if key not in request.form:
                    break
                valor = request.form.get(key, '').strip()
                if valor:
                    cur.execute("""
                        INSERT INTO Menu_Semanal (dia, tipo, plato, semana, orden)
                        VALUES (%s, 'segundo', %s, %s, %s)
                    """, (dia, valor, semana, i))
                i += 1
            i = 0
            while True:
                key = f'bebida_{dia}_{i}'
                if key not in request.form:
                    break
                valor = request.form.get(key, '').strip()
                if valor:
                    cur.execute("""
                        INSERT INTO Menu_Semanal (dia, tipo, plato, semana, orden)
                        VALUES (%s, 'bebida', %s, %s, %s)
                    """, (dia, valor, semana, i))
                i += 1
        conn.commit()
        conn.close()
        flash('¡Menú semanal actualizado! ✅', 'success')
        return redirect(url_for('admin_menu_semanal'))

    cur.execute("""
        SELECT dia, tipo, plato, semana, orden
        FROM Menu_Semanal
        ORDER BY
          CASE dia
            WHEN 'Lunes'     THEN 1
            WHEN 'Martes'    THEN 2
            WHEN 'Miércoles' THEN 3
            WHEN 'Jueves'    THEN 4
            WHEN 'Viernes'   THEN 5
            WHEN 'Sábado'    THEN 6
          END, tipo, orden
    """)
    filas = cur.fetchall()

    menu = {}
    semana_actual = ''
    for dia, tipo, plato, semana, orden in filas:
        if dia not in menu:
            menu[dia] = {'entradas': [], 'segundos': [], 'bebidas': []}
        if semana:
            semana_actual = semana
        if tipo == 'entrada':
            menu[dia]['entradas'].append(plato)
        elif tipo == 'segundo':
            menu[dia]['segundos'].append(plato)
        elif tipo == 'bebida':
            menu[dia]['bebidas'].append(plato)

    cur.execute("SELECT nombre FROM Bebida WHERE disponible = TRUE ORDER BY nombre")
    nombres_bebidas = [r[0] for r in cur.fetchall()]
    conn.close()

    return render_template('admin_menu_semanal.html', menu=menu, semana_actual=semana_actual, nombres_bebidas=nombres_bebidas)

# ╔══════════════════════════════════════════════════════╗
# ║  PLATOS — Admin: agregar nuevos platos al catálogo   ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/admin/platos', methods=['GET', 'POST'])
def admin_platos():
    if not session.get('es_admin'):
        return redirect(url_for('admin_login'))

    conn = get_connection()
    cur  = conn.cursor()

    if request.method == 'POST':
        nombre  = request.form.get('nombre', '').strip()
        precio  = request.form.get('precio', '').strip()
        tipo    = request.form.get('tipo', 'segundo')
        archivo = request.files.get('imagen')

        if not nombre or not precio:
            flash('El nombre y el precio son obligatorios.', 'danger')
            conn.close()
            return redirect(url_for('admin_platos'))

        try:
            precio_val = float(precio)
        except ValueError:
            flash('El precio no es válido.', 'danger')
            conn.close()
            return redirect(url_for('admin_platos'))

        ruta_imagen = None
        if archivo and archivo.filename:
            extension = archivo.filename.rsplit('.', 1)[-1].lower()
            if extension in EXTENSIONES_IMG_PERMITIDAS:
                carpeta = 'imagenes_entrada' if tipo == 'entrada' else 'imagenes_plato'
                nombre_archivo = secure_filename(nombre.lower().replace(' ', '_')) + '.' + extension
                ruta_disco = os.path.join(app.root_path, 'static', carpeta, nombre_archivo)
                archivo.save(ruta_disco)
                ruta_imagen = f'{carpeta}/{nombre_archivo}'
            else:
                flash('Formato de imagen no permitido (usa png, jpg, jpeg o webp).', 'danger')
                conn.close()
                return redirect(url_for('admin_platos'))

        cur.execute("""
            INSERT INTO Plato (nombre, precio, tipo, disponible, imagen)
            VALUES (%s, %s, %s, TRUE, %s)
        """, (nombre, precio_val, tipo, ruta_imagen))
        conn.commit()
        conn.close()
        flash(f'¡Plato "{nombre}" agregado al catálogo! 🍽️', 'success')
        return redirect(url_for('admin_platos'))

    cur.execute("SELECT id_plato, nombre, precio, tipo, disponible, imagen FROM Plato ORDER BY tipo, nombre")
    platos = cur.fetchall()
    conn.close()
    return render_template('admin_platos.html', platos=platos)


@app.route('/admin/platos/toggle', methods=['POST'])
def admin_platos_toggle():
    if not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    id_plato = request.form.get('id_plato')
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("UPDATE Plato SET disponible = NOT disponible WHERE id_plato = %s", (id_plato,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/admin/platos/eliminar', methods=['POST'])
def admin_platos_eliminar():
    if not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    id_plato = request.form.get('id_plato')
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM Plato WHERE id_plato = %s", (id_plato,))
        conn.commit()
        ok = True
    except Exception:
        conn.rollback()
        ok = False
    conn.close()
    if not ok:
        return jsonify({'ok': False, 'error': 'No se puede eliminar: el plato ya tiene pedidos asociados. Puedes desactivarlo en su lugar.'}), 400
    return jsonify({'ok': True})

# ╔══════════════════════════════════════════════════════╗
# ║  REGISTRO DE CLIENTE                                 ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre    = request.form['nombre'].strip()
        telefono  = request.form['telefono'].strip()
        direccion = request.form['direccion'].strip()

        if not nombre or not telefono:
            flash('El nombre y teléfono son obligatorios.', 'danger')
            return redirect(url_for('registro'))

        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("SELECT id_cliente, nombre FROM Cliente WHERE telefono = %s", (telefono,))
        existe = cur.fetchone()

        if existe:
            session['id_cliente'] = existe[0]
            session['nombre']     = existe[1]
            conn.close()
            flash(f'¡Bienvenido de vuelta, {existe[1]}!', 'info')
            return redirect(url_for('index'))

        cur.execute(
            "INSERT INTO Cliente (nombre, telefono, direccion_referencia) VALUES (%s, %s, %s)",
            (nombre, telefono, direccion)
        )
        conn.commit()

        cur.execute("SELECT id_cliente FROM Cliente WHERE telefono = %s", (telefono,))
        nuevo = cur.fetchone()
        session['id_cliente'] = nuevo[0]
        session['nombre']     = nombre
        conn.close()

        flash(f'¡Cuenta creada! Bienvenido, {nombre} 🎉', 'success')
        return redirect(url_for('index'))

    return render_template('registro.html')

# ╔══════════════════════════════════════════════════════╗
# ║  API: Opciones de personalización por plato         ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/api/opciones')
def api_opciones():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT id_opcion, accion, ingrediente, costo_extra
        FROM Opcion_Personalizacion
        ORDER BY accion, ingrediente
    """)
    rows = cur.fetchall()
    conn.close()

    opciones = [
        {
            'id_opcion':   r[0],
            'accion':      r[1],
            'ingrediente': r[2],
            'costo_extra': float(r[3])
        }
        for r in rows
    ]
    return jsonify(opciones)

# ╔══════════════════════════════════════════════════════╗
# ║  HACER PEDIDO                                        ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/pedido', methods=['GET', 'POST'])
def pedido():
    if 'id_cliente' not in session:
        flash('Primero debes registrarte para hacer un pedido.', 'warning')
        return redirect(url_for('registro'))

    conn = get_connection()
    cur  = conn.cursor()

    if request.method == 'POST':
        tipo_entrega  = request.form.get('tipo_entrega', 'delivery')
        hora_estimada = request.form.get('hora_estimada', '').strip()
        platos_ids    = request.form.getlist('platos')
        modo_pedido   = request.form.get('modo_pedido', 'entrada')  # entrada | segundo | menu

        # Precios fijos por modo
        PRECIO_ENTRADA = 5.0
        PRECIO_SEGUNDO = 10.0
        PRECIO_MENU    = 11.0
        RECARGO_DELIVERY = 1.0

        if not platos_ids:
            flash('Debes seleccionar al menos un plato.', 'danger')
            conn.close()
            return redirect(url_for('pedido'))

        # Obtener tipo de cada plato seleccionado
        tipos_plato = {}
        for id_plato in platos_ids:
            cur.execute("SELECT tipo FROM Plato WHERE id_plato = %s", (id_plato,))
            row = cur.fetchone()
            if row:
                tipos_plato[id_plato] = row[0]

        # Validar modo menú: cantidades iguales de entradas y segundos
        if modo_pedido == 'menu':
            cant_entradas = sum(
                int(request.form.get(f'cantidad_{pid}', 1))
                for pid in platos_ids if tipos_plato.get(pid) == 'entrada'
            )
            cant_segundos = sum(
                int(request.form.get(f'cantidad_{pid}', 1))
                for pid in platos_ids if tipos_plato.get(pid) == 'segundo'
            )
            if cant_entradas == 0 or cant_segundos == 0 or cant_entradas != cant_segundos:
                flash(f'Menú Completo: debes tener igual cantidad de entradas y segundos ({cant_entradas} entradas / {cant_segundos} segundos).', 'danger')
                conn.close()
                return redirect(url_for('pedido'))

        cur.execute("""
            INSERT INTO Pedido (fecha_pedido, id_cliente, tipo_entrega, hora_estimada, estado, total)
            VALUES (NOW(), %s, %s, %s, 'pendiente', 0)
            RETURNING id_pedido
        """, (session['id_cliente'], tipo_entrega, hora_estimada or None))
        id_pedido = cur.fetchone()[0]
        conn.commit()

        for id_plato in platos_ids:
            tipo_plato = tipos_plato.get(id_plato, 'segundo')

            # Precio base según modo
            if modo_pedido == 'entrada':
                precio_base = PRECIO_ENTRADA
            elif modo_pedido == 'segundo':
                precio_base = PRECIO_SEGUNDO
            else:  # menu
                precio_base = PRECIO_ENTRADA if tipo_plato == 'entrada' else PRECIO_SEGUNDO

            opciones_ids = request.form.getlist(f'opciones_{id_plato}')
            costo_extra  = 0.0
            for op_id in opciones_ids:
                cur.execute("SELECT costo_extra FROM Opcion_Personalizacion WHERE id_opcion = %s", (op_id,))
                op_row = cur.fetchone()
                if op_row:
                    costo_extra += float(op_row[0])

            precio_final = precio_base + costo_extra
            cantidad     = int(request.form.get(f'cantidad_{id_plato}', 1))
            subtotal     = precio_final * cantidad

            cur.execute("""
                INSERT INTO Detalle_Pedido (id_pedido, id_plato, cantidad, precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id_detalle
            """, (id_pedido, id_plato, cantidad, precio_final, subtotal))
            id_detalle = cur.fetchone()[0]

            for op_id in opciones_ids:
                cur.execute("""
                    INSERT INTO Detalle_Personalizacion (id_detalle, id_opcion)
                    VALUES (%s, %s)
                """, (id_detalle, op_id))

        conn.commit()

        # Para menú completo, recalcular total = pares × 11 + extras
        if modo_pedido == 'menu':
            cur.execute("""
                SELECT COALESCE(SUM(dp.subtotal), 0)
                FROM Detalle_Pedido dp
                JOIN Plato pl ON pl.id_plato = dp.id_plato
                WHERE dp.id_pedido = %s AND pl.tipo = 'entrada'
            """, (id_pedido,))
            total_extras_entrada = float(cur.fetchone()[0])

            cur.execute("""
                SELECT COALESCE(SUM(dp.subtotal), 0)
                FROM Detalle_Pedido dp
                JOIN Plato pl ON pl.id_plato = dp.id_plato
                WHERE dp.id_pedido = %s AND pl.tipo = 'segundo'
            """, (id_pedido,))
            total_extras_segundo = float(cur.fetchone()[0])

            pares = cant_entradas  # ya validado que son iguales
            # subtotal real = precio_base * cantidad (sin extras), extras = subtotal - precio_base*cantidad
            extras_totales = (total_extras_entrada - PRECIO_ENTRADA * cant_entradas) + \
                             (total_extras_segundo - PRECIO_SEGUNDO * cant_segundos)
            total_final = pares * PRECIO_MENU + extras_totales
            if tipo_entrega == 'delivery':
                total_final += RECARGO_DELIVERY
            cur.execute("UPDATE Pedido SET total = %s WHERE id_pedido = %s", (total_final, id_pedido))
        else:
            recargo = RECARGO_DELIVERY if tipo_entrega == 'delivery' else 0.0
            cur.execute("""
                UPDATE Pedido SET total = (
                    SELECT COALESCE(SUM(subtotal), 0)
                    FROM Detalle_Pedido WHERE id_pedido = %s
                ) + %s WHERE id_pedido = %s
            """, (id_pedido, recargo, id_pedido))

        conn.commit()
        conn.close()

        flash('¡Pedido realizado con éxito! Pronto lo confirmaremos. 🍽️', 'success')
        return redirect(url_for('mis_pedidos'))

    cur.execute("SELECT id_plato, nombre, precio, tipo FROM Plato WHERE disponible = TRUE ORDER BY tipo, nombre")
    platos = cur.fetchall()

    cur.execute("""
        SELECT po.id_plato, op.id_opcion, op.accion, op.ingrediente, op.costo_extra
        FROM Plato_Opcion po
        JOIN Opcion_Personalizacion op ON op.id_opcion = po.id_opcion
        ORDER BY po.id_plato, op.accion, op.ingrediente
    """)
    filas_opciones = cur.fetchall()
    conn.close()

    opciones_por_plato = {}
    for id_plato, id_opcion, accion, ingrediente, costo_extra in filas_opciones:
        if id_plato not in opciones_por_plato:
            opciones_por_plato[id_plato] = []
        opciones_por_plato[id_plato].append((id_opcion, accion, ingrediente, costo_extra))

    return render_template('pedido.html', platos=platos, opciones_por_plato=opciones_por_plato)

# ╔══════════════════════════════════════════════════════╗
# ║  MIS PEDIDOS                                         ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/mis_pedidos')
def mis_pedidos():
    if 'id_cliente' not in session:
        flash('Debes registrarte primero.', 'warning')
        return redirect(url_for('registro'))

    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT p.id_pedido, p.fecha_pedido, p.tipo_entrega,
               p.hora_estimada, p.estado, p.total
        FROM Pedido p
        WHERE p.id_cliente = %s
        ORDER BY p.fecha_pedido DESC
    """, (session['id_cliente'],))
    pedidos = cur.fetchall()

    detalles_por_pedido = {}
    es_menu_por_pedido = {}
    pares_por_pedido = {}
    for ped in pedidos:
        cur.execute("""
            SELECT pl.nombre, dp.cantidad, dp.precio_unitario, dp.subtotal,
                   dp.id_detalle, pl.tipo
            FROM Detalle_Pedido dp
            JOIN Plato pl ON pl.id_plato = dp.id_plato
            WHERE dp.id_pedido = %s
        """, (ped[0],))
        detalles = cur.fetchall()

        tipos_presentes = set(det[5] for det in detalles)
        es_menu = 'entrada' in tipos_presentes and 'segundo' in tipos_presentes
        es_menu_por_pedido[ped[0]] = es_menu

        cnt_entradas = sum(det[1] for det in detalles if det[5] == 'entrada')
        cnt_segundos = sum(det[1] for det in detalles if det[5] == 'segundo')
        pares_por_pedido[ped[0]] = min(cnt_entradas, cnt_segundos) if es_menu else 0

        detalles_con_pers = []
        for det in detalles:
            cur.execute("""
                SELECT op.accion, op.ingrediente, op.costo_extra
                FROM Detalle_Personalizacion dpers
                JOIN Opcion_Personalizacion op ON op.id_opcion = dpers.id_opcion
                WHERE dpers.id_detalle = %s
            """, (det[4],))
            personalizaciones = cur.fetchall()
            costo_extra_item = sum(float(p[2]) for p in personalizaciones)
            detalles_con_pers.append({
                'nombre':          det[0],
                'cantidad':        det[1],
                'precio_unitario': det[2],
                'subtotal':        det[3],
                'tipo':            det[5],
                'costo_extra':     costo_extra_item,
                'personalizaciones': personalizaciones
            })
        detalles_por_pedido[ped[0]] = detalles_con_pers

    conn.close()
    return render_template('mis_pedidos.html',
                           pedidos=pedidos,
                           detalles=detalles_por_pedido,
                           es_menu=es_menu_por_pedido,
                           pares=pares_por_pedido)

# ╔══════════════════════════════════════════════════════╗
# ║  Helper: detalle de un pedido + detección de menú    ║
# ╚══════════════════════════════════════════════════════╝
def _obtener_detalle_pedido(cur, id_pedido):
    PRECIO_ENTRADA = 5.0
    PRECIO_SEGUNDO = 10.0
    PRECIO_MENU    = 11.0

    cur.execute("""
        SELECT pl.nombre, dp.cantidad, dp.precio_unitario, dp.subtotal, dp.id_detalle, pl.tipo
        FROM Detalle_Pedido dp
        JOIN Plato pl ON pl.id_plato = dp.id_plato
        WHERE dp.id_pedido = %s
    """, (id_pedido,))
    detalles_raw = cur.fetchall()

    tipos_presentes = set(det[5] for det in detalles_raw)
    es_menu = 'entrada' in tipos_presentes and 'segundo' in tipos_presentes

    detalles = []
    cnt_entradas = 0
    cnt_segundos = 0
    extras_totales = 0.0

    for det in detalles_raw:
        cur.execute("""
            SELECT op.accion, op.ingrediente, op.costo_extra
            FROM Detalle_Personalizacion dp2
            JOIN Opcion_Personalizacion op ON op.id_opcion = dp2.id_opcion
            WHERE dp2.id_detalle = %s
        """, (det[4],))
        pers = cur.fetchall()
        costo_extra_item = sum(float(p[2]) for p in pers)

        detalles.append({
            'nombre':    det[0],
            'cantidad':  det[1],
            'precio':    float(det[2]),
            'subtotal':  float(det[3]),
            'tipo':      det[5],
            'costo_extra_unitario': costo_extra_item,
            'pers':      [{'accion': p[0], 'ingrediente': p[1], 'costo': float(p[2])} for p in pers]
        })

        if es_menu:
            if det[5] == 'entrada':
                cnt_entradas += det[1]
                extras_totales += costo_extra_item * det[1]
            elif det[5] == 'segundo':
                cnt_segundos += det[1]
                extras_totales += costo_extra_item * det[1]

    pares = min(cnt_entradas, cnt_segundos) if es_menu else 0

    return {
        'detalles':       detalles,
        'es_menu':        es_menu,
        'pares':          pares,
        'menu_total':     pares * PRECIO_MENU,
        'extras_totales': extras_totales,
    }

# ╔══════════════════════════════════════════════════════╗
# ║  API: Datos del pedido para comprobante (ADMIN)      ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/admin/pedido_comprobante/<int:id_pedido>')
def admin_pedido_comprobante(id_pedido):
    if not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403

    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT p.id_pedido, p.fecha_pedido, p.tipo_entrega, p.hora_estimada,
               p.estado, p.total, c.nombre, c.telefono
        FROM Pedido p
        JOIN Cliente c ON c.id_cliente = p.id_cliente
        WHERE p.id_pedido = %s
    """, (id_pedido,))
    ped = cur.fetchone()

    if not ped:
        conn.close()
        return jsonify({'error': 'Pedido no encontrado'}), 404

    info = _obtener_detalle_pedido(cur, id_pedido)

    conn.close()
    return jsonify({
        'id_pedido':        ped[0],
        'fecha':            ped[1].strftime('%d/%m/%Y'),
        'hora':             ped[1].strftime('%H:%M'),
        'tipo_entrega':     ped[2],
        'estado':           ped[4],
        'total':            float(ped[5]),
        'cliente_nombre':   ped[6],
        'cliente_telefono': ped[7],
        'detalles':         info['detalles'],
        'es_menu':          info['es_menu'],
        'pares':            info['pares'],
        'menu_total':       info['menu_total'],
        'extras_totales':   info['extras_totales'],
    })

# ╔══════════════════════════════════════════════════════╗
# ║  API: Datos del pedido para comprobante              ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/api/pedido_comprobante/<int:id_pedido>')
def api_pedido_comprobante(id_pedido):
    if 'id_cliente' not in session:
        return jsonify({'error': 'No autorizado'}), 403

    conn = get_connection()
    cur  = conn.cursor()

    # Verificar que el pedido pertenece al cliente en sesión
    cur.execute("""
        SELECT p.id_pedido, p.fecha_pedido, p.tipo_entrega, p.hora_estimada,
               p.estado, p.total, c.nombre, c.telefono
        FROM Pedido p
        JOIN Cliente c ON c.id_cliente = p.id_cliente
        WHERE p.id_pedido = %s AND p.id_cliente = %s
    """, (id_pedido, session['id_cliente']))
    ped = cur.fetchone()

    if not ped:
        conn.close()
        return jsonify({'error': 'Pedido no encontrado'}), 404

    info = _obtener_detalle_pedido(cur, id_pedido)

    conn.close()
    return jsonify({
        'id_pedido':      ped[0],
        'fecha':          ped[1].strftime('%d/%m/%Y'),
        'hora':           ped[1].strftime('%H:%M'),
        'tipo_entrega':   ped[2],
        'estado':         ped[4],
        'total':          float(ped[5]),
        'cliente_nombre': ped[6],
        'detalles':       info['detalles'],
        'es_menu':        info['es_menu'],
        'pares':          info['pares'],
        'menu_total':     info['menu_total'],
        'extras_totales': info['extras_totales'],
    })

# ╔══════════════════════════════════════════════════════╗
# ║  PANEL DE ADMINISTRACIÓN                             ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/admin')
def admin():
    if not session.get('es_admin'):
        return redirect(url_for('admin_login'))

    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT p.id_pedido, c.nombre, p.fecha_pedido,
               p.tipo_entrega, p.hora_estimada, p.estado, p.total
        FROM Pedido p
        JOIN Cliente c ON c.id_cliente = p.id_cliente
        ORDER BY p.fecha_pedido DESC
    """)
    pedidos = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM Pedido")
    total_pedidos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM Pedido WHERE estado = 'pendiente'")
    pendientes = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(total), 0) FROM Pedido WHERE estado = 'entregado'")
    ingresos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM Cliente")
    total_clientes = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM Pedido WHERE estado = 'cancelado'")
    total_cancelados = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(total), 0) FROM Pedido WHERE estado = 'cancelado'")
    monto_cancelados = cur.fetchone()[0]

    cur.execute("""
        SELECT DATE(fecha_pedido) as dia, COALESCE(SUM(total), 0) as ganancia
        FROM Pedido WHERE estado = 'entregado'
        AND fecha_pedido >= NOW() - INTERVAL '7 days'
        GROUP BY DATE(fecha_pedido) ORDER BY dia
    """)
    ganancias_por_dia = cur.fetchall()

    cur.execute("""
        SELECT DATE(fecha_pedido) as dia, COUNT(*) as cantidad, COALESCE(SUM(total), 0) as monto
        FROM Pedido WHERE estado = 'cancelado'
        AND fecha_pedido >= NOW() - INTERVAL '7 days'
        GROUP BY DATE(fecha_pedido) ORDER BY dia
    """)
    cancelados_por_dia = cur.fetchall()

    cur.execute("""
        SELECT pl.nombre, SUM(dp.cantidad) as total_vendido
        FROM Detalle_Pedido dp
        JOIN Plato pl ON pl.id_plato = dp.id_plato
        JOIN Pedido p ON p.id_pedido = dp.id_pedido
        WHERE p.estado = 'entregado'
        GROUP BY pl.nombre ORDER BY total_vendido DESC LIMIT 5
    """)
    platos_top = cur.fetchall()

    conn.close()
    return render_template('admin.html',
                           pedidos=pedidos,
                           total_pedidos=total_pedidos,
                           pendientes=pendientes,
                           ingresos=float(ingresos),
                           total_clientes=total_clientes,
                           total_cancelados=total_cancelados,
                           monto_cancelados=float(monto_cancelados),
                           ganancias_por_dia=ganancias_por_dia,
                           cancelados_por_dia=cancelados_por_dia,
                           platos_top=platos_top)

@app.route('/admin/actualizar_estado', methods=['POST'])
def actualizar_estado():
    if not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403

    id_pedido    = request.form.get('id_pedido')
    nuevo_estado = request.form.get('estado')

    estados_validos = ['pendiente', 'confirmado', 'listo', 'entregado', 'cancelado']
    if nuevo_estado not in estados_validos:
        return jsonify({'error': 'Estado inválido'}), 400

    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("UPDATE Pedido SET estado = %s WHERE id_pedido = %s", (nuevo_estado, id_pedido))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'nuevo_estado': nuevo_estado})


@app.route('/admin/eliminar_pedido', methods=['POST'])
def eliminar_pedido():
    if not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403
    id_pedido = request.form.get('id_pedido')
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        DELETE FROM Detalle_Personalizacion
        WHERE id_detalle IN (
            SELECT id_detalle FROM Detalle_Pedido WHERE id_pedido = %s
        )
    """, (id_pedido,))
    cur.execute("DELETE FROM Detalle_Pedido WHERE id_pedido = %s", (id_pedido,))
    cur.execute("DELETE FROM Pedido WHERE id_pedido = %s", (id_pedido,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# ╔══════════════════════════════════════════════════════╗
# ║  CLIENTES — Admin: ver y eliminar registros          ║
# ╚══════════════════════════════════════════════════════╝
def _eliminar_cliente_en_cascada(cur, id_cliente):
    cur.execute("""
        DELETE FROM Detalle_Personalizacion
        WHERE id_detalle IN (
            SELECT dp.id_detalle FROM Detalle_Pedido dp
            JOIN Pedido p ON p.id_pedido = dp.id_pedido
            WHERE p.id_cliente = %s
        )
    """, (id_cliente,))
    cur.execute("""
        DELETE FROM Detalle_Pedido
        WHERE id_pedido IN (SELECT id_pedido FROM Pedido WHERE id_cliente = %s)
    """, (id_cliente,))
    cur.execute("DELETE FROM Pedido WHERE id_cliente = %s", (id_cliente,))
    cur.execute("DELETE FROM Cliente WHERE id_cliente = %s", (id_cliente,))


@app.route('/admin/clientes')
def admin_clientes():
    if not session.get('es_admin'):
        return redirect(url_for('admin_login'))

    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT c.id_cliente, c.nombre, c.telefono, c.direccion_referencia,
               COUNT(p.id_pedido) AS cantidad_pedidos
        FROM Cliente c
        LEFT JOIN Pedido p ON p.id_cliente = c.id_cliente
        GROUP BY c.id_cliente, c.nombre, c.telefono, c.direccion_referencia
        ORDER BY c.nombre, c.id_cliente
    """)
    clientes = cur.fetchall()
    conn.close()
    return render_template('admin_clientes.html', clientes=clientes)


@app.route('/admin/clientes/eliminar_lote', methods=['POST'])
def admin_clientes_eliminar_lote():
    if not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403

    ids = request.form.getlist('ids[]') or request.form.getlist('ids')
    if not ids:
        return jsonify({'error': 'No se seleccionó ningún cliente.'}), 400

    conn = get_connection()
    cur  = conn.cursor()
    try:
        for id_cliente in ids:
            _eliminar_cliente_en_cascada(cur, id_cliente)
        conn.commit()
        eliminados = len(ids)
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': f'Error al eliminar: {str(e)[:150]}'}), 500

    conn.close()
    return jsonify({'ok': True, 'eliminados': eliminados})

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'admin123':
            session['es_admin'] = True
            return redirect(url_for('admin'))
        flash('Contraseña incorrecta.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('es_admin', None)
    return redirect(url_for('index'))

# ╔══════════════════════════════════════════════════════╗
# ║  CERRAR SESIÓN                                       ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/salir')
def salir():
    nombre = session.get('nombre', '')
    session.pop('id_cliente', None)
    session.pop('nombre', None)
    flash(f'Hasta pronto, {nombre}. 👋', 'info')
    return redirect(url_for('index'))

# ╔══════════════════════════════════════════════════════╗
# ║  REPORTES ADMIN                                      ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/admin/reportes')
def admin_reportes():
    if not session.get('es_admin'):
        return redirect(url_for('admin_login'))

    rangos_dias = {'semana': 7, 'mes': 30, '3meses': 90}
    rango = request.args.get('rango', 'mes')
    if rango not in rangos_dias:
        rango = 'mes'
    dias = rangos_dias[rango]

    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("SELECT COALESCE(SUM(total), 0) FROM Pedido WHERE estado = 'entregado'")
    ingresos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM Pedido WHERE estado = 'cancelado'")
    total_cancelados = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(total), 0) FROM Pedido WHERE estado = 'cancelado'")
    monto_cancelados = cur.fetchone()[0]

    cur.execute("""
        SELECT DATE(fecha_pedido) as dia, COALESCE(SUM(total), 0) as ganancia
        FROM Pedido WHERE estado = 'entregado'
        AND fecha_pedido >= NOW() - (%s || ' days')::interval
        GROUP BY DATE(fecha_pedido) ORDER BY dia
    """, (dias,))
    ganancias_por_dia = cur.fetchall()

    cur.execute("""
        SELECT DATE(fecha_pedido) as dia, COUNT(*) as cantidad, COALESCE(SUM(total), 0) as monto
        FROM Pedido WHERE estado = 'cancelado'
        AND fecha_pedido >= NOW() - (%s || ' days')::interval
        GROUP BY DATE(fecha_pedido) ORDER BY dia
    """, (dias,))
    cancelados_por_dia = cur.fetchall()

    cur.execute("""
        SELECT pl.nombre, SUM(dp.cantidad) as total_vendido
        FROM Detalle_Pedido dp
        JOIN Plato pl ON pl.id_plato = dp.id_plato
        JOIN Pedido p ON p.id_pedido = dp.id_pedido
        WHERE p.estado = 'entregado'
        GROUP BY pl.nombre ORDER BY total_vendido DESC LIMIT 5
    """)
    platos_top = cur.fetchall()

    cur.execute("""
        SELECT p.id_pedido, c.nombre, p.fecha_pedido, p.total
        FROM Pedido p JOIN Cliente c ON c.id_cliente = p.id_cliente
        WHERE p.estado = 'cancelado'
        ORDER BY p.fecha_pedido DESC LIMIT 10
    """)
    cancelados_recientes = cur.fetchall()

    conn.close()
    return render_template('admin_reportes.html',
        ingresos=float(ingresos),
        total_cancelados=total_cancelados,
        monto_cancelados=float(monto_cancelados),
        ganancias_por_dia=ganancias_por_dia,
        cancelados_por_dia=cancelados_por_dia,
        platos_top=platos_top,
        cancelados_recientes=cancelados_recientes,
        rango_actual=rango)

# ╔══════════════════════════════════════════════════════╗
# ║  RECLAMOS — Página pública                           ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/reclamos')
def reclamos():
    mis_reclamos = []
    if 'id_cliente' in session:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT id_reclamo, fecha_reclamo, asunto, mensaje, estado
            FROM Reclamo
            WHERE id_cliente = %s
            ORDER BY fecha_reclamo DESC
        """, (session['id_cliente'],))
        mis_reclamos = cur.fetchall()
        conn.close()
    return render_template('reclamos.html', mis_reclamos=mis_reclamos)


@app.route('/reclamos/enviar', methods=['POST'])
def reclamos_enviar():
    nombre  = request.form.get('nombre', '').strip()
    celular = request.form.get('celular', '').strip()
    email   = request.form.get('email', '').strip()
    asunto  = request.form.get('asunto', '').strip()
    mensaje = request.form.get('mensaje', '').strip()

    if not nombre or not asunto or not mensaje:
        return jsonify({'ok': False, 'error': 'Faltan campos obligatorios.'}), 400
    if not celular and not email:
        return jsonify({'ok': False, 'error': 'Ingresa al menos un medio de contacto.'}), 400

    id_cliente = session.get('id_cliente')

    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO Reclamo (nombre, celular, email, asunto, mensaje, id_cliente)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (nombre, celular or None, email or None, asunto, mensaje, id_cliente))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ╔══════════════════════════════════════════════════╗
# ║  RECLAMOS — Admin: ver, cambiar estado, eliminar ║
# ╚══════════════════════════════════════════════════╝
@app.route('/admin/reclamos')
def admin_reclamos():
    if not session.get('es_admin'):
        return redirect(url_for('admin_login'))

    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM Reclamo")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM Reclamo WHERE estado = 'nuevo'")
    nuevos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM Reclamo WHERE estado = 'resuelto'")
    resueltos = cur.fetchone()[0]

    cur.execute("""
        SELECT id_reclamo, fecha_reclamo, nombre, celular, email,
               asunto, mensaje, estado, estado
        FROM Reclamo
        ORDER BY fecha_reclamo DESC
    """)
    reclamos = cur.fetchall()
    conn.close()

    return render_template('admin_reclamos.html',
                           reclamos=reclamos,
                           total=total,
                           nuevos=nuevos,
                           resueltos=resueltos)


@app.route('/admin/reclamos/estado', methods=['POST'])
def admin_reclamos_estado():
    if not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403

    id_reclamo = request.form.get('id_reclamo')
    estado     = request.form.get('estado')

    if estado not in ('nuevo', 'en_revision', 'resuelto'):
        return jsonify({'error': 'Estado inválido'}), 400

    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("UPDATE Reclamo SET estado = %s WHERE id_reclamo = %s", (estado, id_reclamo))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/admin/reclamos/eliminar', methods=['POST'])
def admin_reclamos_eliminar():
    if not session.get('es_admin'):
        return jsonify({'error': 'No autorizado'}), 403

    id_reclamo = request.form.get('id_reclamo')
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM Reclamo WHERE id_reclamo = %s", (id_reclamo,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ╔══════════════════════════════════════════════════════════╗
# ║  DIAGNÓSTICO                                            ║
# ╚══════════════════════════════════════════════════════════╝
@app.route('/diagnostico')
def diagnostico():
    resultados = []
    bd_ok = False
    try:
        conn = get_connection()
        conn.close()
        resultados.append(('Conexión a PostgreSQL', 'OK - Conexión exitosa', True))
        bd_ok = True
    except Exception as e:
        resultados.append(('Conexión a PostgreSQL', str(e)[:120], False))

    tabla_resultados = []
    if bd_ok:
        try:
            conn = get_connection()
            cur = conn.cursor()
            for tabla in ['Cliente','Plato','Opcion_Personalizacion',
                          'Pedido','Detalle_Pedido','Detalle_Personalizacion','Menu_Semanal','Bebida']:
                cur.execute(f"SELECT COUNT(*) FROM {tabla}")
                n = cur.fetchone()[0]
                tabla_resultados.append((tabla, n, n > 0))
            conn.close()
        except Exception as e:
            tabla_resultados.append(('Error', str(e), False))

    css = """<!DOCTYPE html><html lang="es"><head>
    <meta charset="UTF-8"><title>Diagnóstico</title>
    <link href="https://fonts.googleapis.com/css2?family=Jost:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
      body{font-family:'Jost',sans-serif;background:#FDF3E3;color:#2D1B00;margin:0;padding:2rem}
      h1{color:#8B1A1A;font-size:1.8rem;margin-bottom:.3rem}
      .card{background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.1);padding:1.5rem;margin-bottom:1.5rem}
      .row{display:flex;align-items:center;gap:1rem;padding:.6rem 0;border-bottom:1px solid #F0E4CC;font-size:.9rem}
      .row:last-child{border-bottom:none}
      .ico{font-size:1.1rem;width:1.5rem} .label{font-weight:600;min-width:220px}
      .val{color:#6B5B4B;flex:1} .num{font-weight:700;color:#2C4A1E;min-width:60px;text-align:right}
      a{display:inline-block;margin-top:1rem;background:#8B1A1A;color:#fff;padding:.6rem 1.4rem;border-radius:6px;text-decoration:none;font-weight:600}
    </style></head><body>
    <h1>🔍 Diagnóstico</h1>"""

    filas = "".join(f'<div class="row"><span class="ico">{"✅" if ok else "❌"}</span><span class="label">{l}</span><span class="val">{v}</span></div>' for l,v,ok in resultados)
    filas_t = "".join(f'<div class="row"><span class="ico">{"✅" if ok else "⚠️"}</span><span class="label">{t}</span><span class="num">{n} filas</span></div>' for t,n,ok in tabla_resultados)

    html = css + f'<div class="card"><h2>Conexión</h2>{filas}</div>'
    if filas_t:
        html += f'<div class="card"><h2>Tablas</h2>{filas_t}</div>'
    html += '<a href="/">← Volver</a></body></html>'
    return html

if __name__ == '__main__':
    app.run(debug=True)
