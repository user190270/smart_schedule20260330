FROM node:20-alpine

WORKDIR /app

COPY package.json /app/package.json

RUN npm config set registry https://registry.npmmirror.com \
    && npm install

COPY . /app

EXPOSE 5173

CMD ["npm", "run", "dev"]

