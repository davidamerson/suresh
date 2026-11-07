import frida
import json
import threading

script_source = r"""
Java.perform(function () {
    try {
        const DB = Java.use('android.database.sqlite.SQLiteDatabase');
        const Splash = Java.use('com.cy.cybertv.SplashScreen');
        const native = Splash.nativeDecryptName.overload('java.lang.String');
        const db = DB.openDatabase('/data/user/0/com.cy.cybertv/databases/channelss.db', null, DB.OPEN_READONLY.value);
        const cursor = db.rawQuery("SELECT channels_name,link,type FROM tvlist WHERE categories='Local' LIMIT 30", null);
        let total = 0;
        while (cursor.moveToNext()) {
            const name = String(cursor.getString(0));
            const encoded = String(cursor.getString(1));
            const category = String(cursor.getString(2));
            if (!/^(Hiru TV|Rupavahini|Siyatha TV|Sirasa TV|TV Derana|ITN|Swarnavahini|Shakthi TV|Vasantham TV|Nethra TV|TV1|Supreme TV|Ada Derana 24)$/.test(name)) continue;
            let result = null;
            let error = "";
            try {
                result = String(native.call(Splash, encoded));
            } catch(e) {
                error = String(e).slice(0, 150);
            }
            const text = result || "";
            const hosts = [];
            const regex = /https?:\/\/([a-z0-9.-]+)/ig;
            let m;
            while((m=regex.exec(text)) !== null) {
                if (hosts.indexOf(m[1]) < 0) hosts.push(m[1]);
            }
            send({type:'CHANNEL_CLASSIFICATION',name:name,group:category,
                inputLength:encoded.length,inputHex:/^[a-f0-9]+$/i.test(encoded),
                resultLength:text.length,validHttp:/^https?:\/\//i.test(text),
                hosts:hosts.slice(0,5),hls:/\.m3u8/i.test(text),
                dash:/\.mpd/i.test(text),referencesDRM:/widevine|clearkey|drm|license/i.test(text),
                referencesPRO:/\bPRO\b/i.test(text),
                containsSignedOrAuth:/[?&](token|sig|expires|auth|key)=/i.test(text),
                resultEmpty:!text || text==='null',
                error:error});
            total++;
        }
        cursor.close();
        db.close();
        send({type:'SUMMARY',tested:total});
    } catch (e) {
        send({type:'TEST_ERROR',error:String(e).slice(0,300)});
    }
});
"""
ready = threading.Event()
def message(msg,data):
    if msg['type']=='send':
        payload=msg['payload']
        print('FRIDA_RESULT',json.dumps(payload,sort_keys=True),flush=True)
        if payload.get('type') in ('SUMMARY','TEST_ERROR'):ready.set()
    else:
        print('FRIDA_EXCEPTION',str(msg.get('stack') or msg)[:450],flush=True)
        ready.set()
try:
    device=frida.get_usb_device(timeout=20)
    app=device.get_process('com.cy.cybertv')
    print('ATTACHED_PID',app.pid,flush=True)
    session=device.attach(app.pid)
    script=session.create_script(script_source)
    script.on('message',message)
    script.load()
    ready.wait(timeout=40)
    script.unload()
    session.detach()
except Exception as e:
    print('FRIDA_CONNECT_ERROR',repr(e),flush=True)
print('CLASSIFICATION_COMPLETE')
