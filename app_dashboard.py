# -----------------------------------------------------------------------------
        # SECCIÓN DINÁMICA DE UPRES APILADO (TOP 1 BASE -> TOP 2 -> TOP 3 -> OTROS AL FINAL)
        # -----------------------------------------------------------------------------
        st.subheader("🏢 Distribución por UPRES (Top 10)")
        
        dim_apilamiento = st.radio(
            "Seleccione dimensión de apilamiento:",
            ["Categoría Salud", "Motivo Específico"],
            horizontal=True
        )

        top_10_upres = df_base['UNIDAD DE ASIGNACIÓN'].value_counts().head(10).index
        df_g2 = df_base[df_base['UNIDAD DE ASIGNACIÓN'].isin(top_10_upres)].copy()

        col_target = 'ESPECIALIDAD_CATEGORIA' if dim_apilamiento == "Categoría Salud" else col_mot_esp

        # 1. Obtener los 3 ítems con mayor frecuencia en la dimensión seleccionada
        top_3_items = df_g2[col_target].value_counts().head(3).index.tolist()

        # 2. Asignar los elementos fuera del Top 3 a la categoría "OTROS"
        df_g2['Grupo_Consolidado'] = df_g2[col_target].apply(
            lambda x: x if x in top_3_items else "OTROS"
        )

        # 3. Agrupar y abreviar etiquetas sin recortar con "..."
        df_stack = df_g2.groupby(['UNIDAD DE ASIGNACIÓN', 'Grupo_Consolidado']).size().reset_index(name='Cantidad')
        df_stack['UPRES_fmt'] = df_stack['UNIDAD DE ASIGNACIÓN'].apply(acortar_texto_abreviado)
        df_stack['Grupo_fmt'] = df_stack['Grupo_Consolidado'].apply(
            lambda x: "OTROS" if x == "OTROS" else acortar_texto_abreviado(x)
        )

        # 4. ORDEN INVERSO DE APILAMIENTO:
        # Para que el Top 1 aparezca al inicio (izquierda) y "OTROS" al final (punta derecha):
        top_3_fmt = [acortar_texto_abreviado(x) for x in top_3_items]
        
        # Secuencia: OTROS, Top 3, Top 2, Top 1
        orden_apilado_inverso = ["OTROS"] + top_3_fmt[::-1]

        fig_stack = px.bar(
            df_stack, 
            y='UPRES_fmt', 
            x='Cantidad', 
            color='Grupo_fmt', 
            orientation='h',
            category_orders={'Grupo_fmt': orden_apilado_inverso},
            color_discrete_map={
                top_3_fmt[0]: '#1b5e20',  # Top 1 (Verde oscuro en la base)
                top_3_fmt[1]: '#2e7d32',  # Top 2 (Verde medio)
                top_3_fmt[2]: '#43a047',  # Top 3 (Verde claro)
                'OTROS': '#a5d6a7'        # OTROS (Verde muy suave en la punta derecha)
            }
        )
        fig_stack.update_layout(
            barmode='stack',
            yaxis=dict(autorange="reversed"), 
            xaxis_title="", yaxis_title="", 
            height=440, 
            margin=dict(l=5, r=5, t=10, b=10),
            legend=dict(
                orientation="h", 
                y=-0.25, 
                x=0,
                title=None,
                font=dict(size=10)
            )
        )
        st.plotly_chart(aplicar_touch_safe(fig_stack), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)