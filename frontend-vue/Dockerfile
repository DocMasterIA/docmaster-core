GNU nano 7.2                                                                                                                                                                                                               docmaster-core/frontend-vue/Dockerfile *                                                                                                                                                                                                                       

# Se usar yarn, troque para: COPY package.json yarn.lock ./
# Se usar pnpm, troque para: COPY package.json pnpm-lock.yaml ./

# Instala dependências
RUN npm install --legacy-peer-deps

# Copia o restante do código
COPY . .

# Build de produção (gera /dist)
RUN npm run build

# ---------------------------------------------------
# Etapa 2: imagem final, leve, servindo com Nginx
FROM nginx:stable-alpine

# Remove configuração padrão e adiciona a nossa (opcional, mas recomendado)
RUN rm /etc/nginx/conf.d/default.conf

# Configuração simples para servir a app SPA do Vue
# (se já tiver um nginx.conf no projeto, apenas COPY ele em vez deste bloco)
RUN printf 'server {\n\
    listen 80;\n\
    server_name _;\n\
    root /usr/share/nginx/html;\n\
\n\
    index index.html;\n\
\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/vue.conf

# Copia arquivos estáticos gerados pelo build do Vue
COPY --from=build /app/dist /usr/share/nginx/html

# Expõe a porta HTTP
EXPOSE 80

# Comando padrão do Nginx
CMD ["nginx", "-g", "daemon off;"]





