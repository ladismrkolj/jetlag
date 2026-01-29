Avoid jetlag

Calculations now run entirely in the frontend with no Python backend required, and the previous Python backend package/tests have been removed.

```
cd /opt/jetlag/frontend
git pull
npm install          # only if package.json / lock changed
npm run build
pm2 reload jetlag --update-env
```
