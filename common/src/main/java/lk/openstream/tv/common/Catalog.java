package lk.openstream.tv.common;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.List;

public final class Catalog {
    private Catalog(){}
    public static final String REMOTE_URL =
      "https://raw.githubusercontent.com/davidamerson/suresh/sltv-two-tv-apps-20261109/catalog/channels.json";
    public interface Listener { void onReady(List<Channel> channels,boolean refreshed); }
    public static List<Channel> parse(String json) throws Exception {
        JSONObject doc=new JSONObject(json);
        JSONArray data=doc.getJSONArray("channels");
        List<Channel> list=new ArrayList<>();
        for(int i=0;i<data.length();i++) {
            JSONObject j=data.optJSONObject(i);
            if(j!=null && j.optString("name","").length()>0)list.add(Channel.fromJson(j));
        }
        return list;
    }
    private static String read(InputStream in) throws Exception {
        try(InputStream source=in;ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            byte[] b=new byte[8192];int n;
            while((n=source.read(b))>=0) {
                out.write(b,0,n);
                if(out.size()>2000000)throw new IllegalStateException("catalog too large");
            }
            return out.toString("UTF-8");
        }
    }
    public static void load(Activity activity,Listener listener) {
        SharedPreferences prefs=activity.getSharedPreferences("openstream_catalog",Context.MODE_PRIVATE);
        String fallback=prefs.getString("cached",null);
        try {
            if(fallback==null)fallback=read(activity.getAssets().open("channels.json"));
            listener.onReady(parse(fallback),false);
        } catch(Exception e) { listener.onReady(new ArrayList<>(),false); }
        new Thread(()-> {
            HttpURLConnection conn=null;
            try {
                conn=(HttpURLConnection)new URL(REMOTE_URL+"?v="+System.currentTimeMillis()).openConnection();
                conn.setRequestProperty("Accept","application/json");
                conn.setConnectTimeout(6500);conn.setReadTimeout(6500);
                if(conn.getResponseCode()!=200)return;
                String payload=read(conn.getInputStream());
                List<Channel> list=parse(payload);
                if(list.size()<10)return;
                prefs.edit().putString("cached",payload).apply();
                activity.runOnUiThread(()->listener.onReady(list,true));
            } catch(Exception ignored) {}
            finally {if(conn!=null)conn.disconnect();}
        },"catalog-refresh").start();
    }
}
