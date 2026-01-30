Avoid jetlag

Calculations now run entirely in the frontend with no Python backend required, and the previous Python backend package/tests have been removed.

```
cd /opt/jetlag
git pull
npm install          # never on prod server. only if package.json / lock changed
npm run build
pm2 reload jetlag --update-env
```
