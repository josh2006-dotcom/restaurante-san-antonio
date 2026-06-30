from flask import (Flask, render_template, request,
                   redirect, url_for, session, flash, jsonify)
from database import get_connection

app = Flask(__name__)
app.secret_key = 'restaurante_san_antonio_clave_secreta_2024'

# ╔══════════════════════════════════════════════════════╗
# ║  INICIO — Menú público                               ║
# ╚══════════════════════════════════════════════════════╝
@app.route('/')
def index():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT id_plato, nombre, precio, tipo FROM Plato WHERE disponible = TRUE ORDER BY tipo, nombre")
    platos = cur.fetchall()
    conn.close()
    return render_template('index.html', platos=platos)

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

    # Agrupar por dia: { dia: { entradas: [...], segundos: [...], semana: '' } }
    menu = {}
    for dia, tipo, plato, semana, orden in filas:
        if dia not in menu:
            menu[dia] = {'entradas': [], 'segundos': [], 'semana': semana}
        if tipo == 'entrada':
            menu[dia]['entradas'].append(plato)
        else:
            menu[dia]['segundos'].append(plato)

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
            # Entradas (pueden venir varias: entrada_Lunes_0, entrada_Lunes_1, ...)
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
            # Segundos
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
    conn.close()

    menu = {}
    semana_actual = ''
    for dia, tipo, plato, semana, orden in filas:
        if dia not in menu:
            menu[dia] = {'entradas': [], 'segundos': []}
        if semana:
            semana_actual = semana
        if tipo == 'entrada':
            menu[dia]['entradas'].append(plato)
        else:
            menu[dia]['segundos'].append(plato)

    return render_template('admin_menu_semanal.html', menu=menu, semana_actual=semana_actual)

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

        if not platos_ids:
            flash('Debes seleccionar al menos un plato.', 'danger')
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
            cur.execute("SELECT precio FROM Plato WHERE id_plato = %s", (id_plato,))
            row = cur.fetchone()
            if not row:
                continue
            precio_base = float(row[0])

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

        cur.execute("""
            UPDATE Pedido
            SET total = (
                SELECT COALESCE(SUM(subtotal), 0)
                FROM Detalle_Pedido
                WHERE id_pedido = %s
            )
            WHERE id_pedido = %s
        """, (id_pedido, id_pedido))
        conn.commit()
        conn.close()

        flash('¡Pedido realizado con éxito! Pronto lo confirmaremos. 🍽️', 'success')
        return redirect(url_for('mis_pedidos'))

    cur.execute("SELECT id_plato, nombre, precio, tipo FROM Plato WHERE disponible = TRUE ORDER BY tipo, nombre")
    platos = cur.fetchall()
    cur.execute("SELECT id_opcion, accion, ingrediente, costo_extra FROM Opcion_Personalizacion ORDER BY accion")
    opciones = cur.fetchall()
    conn.close()

    return render_template('pedido.html', platos=platos, opciones=opciones)

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
    for ped in pedidos:
        cur.execute("""
            SELECT pl.nombre, dp.cantidad, dp.precio_unitario, dp.subtotal,
                   dp.id_detalle
            FROM Detalle_Pedido dp
            JOIN Plato pl ON pl.id_plato = dp.id_plato
            WHERE dp.id_pedido = %s
        """, (ped[0],))
        detalles = cur.fetchall()

        detalles_con_pers = []
        for det in detalles:
            cur.execute("""
                SELECT op.accion, op.ingrediente, op.costo_extra
                FROM Detalle_Personalizacion dpers
                JOIN Opcion_Personalizacion op ON op.id_opcion = dpers.id_opcion
                WHERE dpers.id_detalle = %s
            """, (det[4],))
            personalizaciones = cur.fetchall()
            detalles_con_pers.append({
                'nombre':          det[0],
                'cantidad':        det[1],
                'precio_unitario': det[2],
                'subtotal':        det[3],
                'personalizaciones': personalizaciones
            })
        detalles_por_pedido[ped[0]] = detalles_con_pers

    conn.close()
    return render_template('mis_pedidos.html',
                           pedidos=pedidos,
                           detalles=detalles_por_pedido)

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

    # Ganancias por dia (ultimos 7 dias)
    cur.execute("""
        SELECT DATE(fecha_pedido) as dia, COALESCE(SUM(total), 0) as ganancia
        FROM Pedido WHERE estado = 'entregado'
        AND fecha_pedido >= NOW() - INTERVAL '7 days'
        GROUP BY DATE(fecha_pedido)
        ORDER BY dia
    """)
    ganancias_por_dia = cur.fetchall()

    # Cancelados por dia (ultimos 7 dias)
    cur.execute("""
        SELECT DATE(fecha_pedido) as dia, COUNT(*) as cantidad, COALESCE(SUM(total), 0) as monto
        FROM Pedido WHERE estado = 'cancelado'
        AND fecha_pedido >= NOW() - INTERVAL '7 days'
        GROUP BY DATE(fecha_pedido)
        ORDER BY dia
    """)
    cancelados_por_dia = cur.fetchall()

    # Platos mas vendidos
    cur.execute("""
        SELECT pl.nombre, SUM(dp.cantidad) as total_vendido
        FROM Detalle_Pedido dp
        JOIN Plato pl ON pl.id_plato = dp.id_plato
        JOIN Pedido p ON p.id_pedido = dp.id_pedido
        WHERE p.estado = 'entregado'
        GROUP BY pl.nombre
        ORDER BY total_vendido DESC
        LIMIT 5
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
        AND fecha_pedido >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(fecha_pedido) ORDER BY dia
    """)
    ganancias_por_dia = cur.fetchall()

    cur.execute("""
        SELECT DATE(fecha_pedido) as dia, COUNT(*) as cantidad, COALESCE(SUM(total), 0) as monto
        FROM Pedido WHERE estado = 'cancelado'
        AND fecha_pedido >= NOW() - INTERVAL '30 days'
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
        cancelados_recientes=cancelados_recientes)

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
                          'Pedido','Detalle_Pedido','Detalle_Personalizacion','Menu_Semanal']:
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
