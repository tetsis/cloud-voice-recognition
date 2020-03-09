# Docker image
## Image build
```
docker build -t tetsis/cloud-voice-recognition-proxy:latest -f proxy/Dockerfile .
docker build -t tetsis/cloud-voice-recognition-api:latest -f api/Dockerfile .
```

## Log in Docker Hub
```
docker login
```

## Push image to Docke Hub
```
docker push tetsis/cloud-voice-recognition-proxy:latest
docker push tetsis/cloud-voice-recognition-api:latest
```

# Amplify
## Install Amplify
```
npm install -g @aws-amplify/cli
```

## Configure
```
amplify configure
```

## Initialize Amplify
Chage directory to project folder, then run this command.
```
amplify init
```

## Web hosting
You can select `PROD` to use https access.
```
amplify hosting add
Select the environment setup: PROD (S3 with CloudFront using HTTPS)
```

## Publish
```
amplify publish
```

## Bug fix
Amplifyの不具合でCloudFrontの設定不足によりAccess Deniedになるため以下を修正
- CloudFrontページにアクセス
- Distributionsから該当のものを選択
- Origins and Origin GroupsのOriginsで「Edit」をクリック
- Restrict Bucket Accessを「Yes」にする
- Origin Access Identityを「Use an Existing Identity」を選択
- Your Identitiesを選択
- Grant Read Permissions on Bucketで「Yes, Update Bucket Policy」を選択
- 「Yes, Edit」をクリック

## Auth
```
amplify add auth
```

## Install Node.js packages
```
npm install aws-amplify
npm install aws-amplify-vue
```







# [Vue Paper Dashboard](https://cristijora.github.io/vue-paper-dashboard/)

> Admin dashboard based on paper dashboard UI template + vue-router

This project is a vue version of [Paper-dashboard](https://www.creative-tim.com/product/paper-dashboard)
designed for vue js.The dashboard includes vue-router

Check the [Live Demo here](https://cristijora.github.io/vue-paper-dashboard).

[Nuxt Version (outdated Bootstrap 3)](https://github.com/cristijora/vue-paper-dashboard-nuxt)
![](http://i.imgur.com/3iC1hOs.gif)

## Documentation
Link to [Documentation](http://vuejs.creative-tim.com/vue-paper-dashboard/documentation/)

## Build Setup

### install dependencies
```
npm install
```
### serve with hot reload at localhost:8080
```
npm run dev
```
### build for production with minification
```
npm run build
```
### lint
```
npm run lint
```
## Contribution guide
* Fork the repository
* `npm install` or `yarn install`
* Make changes
* Open Pull Request

For detailed explanation on how things work, checkout the [guide](https://github.com/vuejs/vue-cli/blob/dev/docs/README.md)
- [CHANGELOG](./CHANGELOG.md)
- [version-badge](https://img.shields.io/badge/version-2.0.0-blue.svg)
- [license-badge](https://img.shields.io/badge/license-MIT-blue.svg)

## License

[MIT](https://github.com/cristijora/vue-paper-dashboard/blob/master/LICENSE.md)
