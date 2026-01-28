Avoid jetlag

```
cd /opt/jetlag/frontend
git pull
npm install          # only if package.json / lock changed
npm run build
pm2 reload jetlag --update-env
```
