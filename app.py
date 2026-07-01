# ─────────────────────────────────────────────────────────────────
# REEMPLAZA el bloque "if request.method == 'POST':" dentro de
# la función admin_menu_semanal() en app.py por este código:
# ─────────────────────────────────────────────────────────────────

    if request.method == 'POST':
        dias = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado']
        semana = request.form.get('semana', '')
        cur.execute("DELETE FROM Menu_Semanal")

        for dia in dias:
            # Recoge TODOS los campos que empiecen con el prefijo correcto
            # sin importar el índice (puede ser 0,1,2 o un timestamp)
            for key, valor in request.form.items():
                if key.startswith('entrada_' + dia + '_') and valor.strip():
                    orden = key.split('_')[-1]
                    cur.execute("""
                        INSERT INTO Menu_Semanal (dia, tipo, plato, semana, orden)
                        VALUES (%s, 'entrada', %s, %s, %s)
                    """, (dia, valor.strip(), semana, orden))

            for key, valor in request.form.items():
                if key.startswith('segundo_' + dia + '_') and valor.strip():
                    orden = key.split('_')[-1]
                    cur.execute("""
                        INSERT INTO Menu_Semanal (dia, tipo, plato, semana, orden)
                        VALUES (%s, 'segundo', %s, %s, %s)
                    """, (dia, valor.strip(), semana, orden))

            for key, valor in request.form.items():
                if key.startswith('bebida_' + dia + '_') and valor.strip():
                    orden = key.split('_')[-1]
                    cur.execute("""
                        INSERT INTO Menu_Semanal (dia, tipo, plato, semana, orden)
                        VALUES (%s, 'bebida', %s, %s, %s)
                    """, (dia, valor.strip(), semana, orden))

        conn.commit()
        conn.close()
        flash('¡Menú semanal actualizado! ✅', 'success')
        return redirect(url_for('admin_menu_semanal'))
