# -----------------------------------------------------------------------------
        # Gráfico 1: Mapa Geográfico de Colombia por UPRES (Corregido con px.scatter_map)
        # -----------------------------------------------------------------------------
        st.subheader("🗺️ Mapa de Colombia con SIPQR2S por UPRES")
        df_geo = df_base.groupby('UNIDAD DE ASIGNACIÓN').size().reset_index(name='Cantidad')
        
        # Mapeo de coordenadas aproximadas por concordancia de texto
        lats, lons = [], []
        for u in df_geo['UNIDAD DE ASIGNACIÓN']:
            matched = False
            for dep, coords in GEO_DEPARTAMENTOS_COL.items():
                if dep in str(u).upper():
                    lats.append(coords[0])
                    lons.append(coords[1])
                    matched = True
                    break
            if not matched:
                lats.append(4.6097) # Coordenada por defecto (Bogotá)
                lons.append(-74.0817)

        df_geo['lat'] = lats
        df_geo['lon'] = lons
        
        # Usamos px.scatter_map en lugar del obsoleto px.scatter_mapbox
        fig_mapa = px.scatter_map(
            df_geo, 
            lat='lat', 
            lon='lon', 
            size='Cantidad', 
            hover_name='UNIDAD DE ASIGNACIÓN',
            hover_data={'Cantidad': True, 'lat': False, 'lon': False},
            color='Cantidad',
            color_continuous_scale=px.colors.cyclical.IceFire,
            zoom=4.2,
            center={"lat": 4.5709, "lon": -74.2973},
            map_style="open-street-map"
        )
        fig_mapa.update_layout(height=350, margin=dict(l=5, r=5, t=10, b=10))
        st.plotly_chart(aplicar_touch_safe(fig_mapa), use_container_width=True, config=CONFIG_PLOTLY_TOUCH)