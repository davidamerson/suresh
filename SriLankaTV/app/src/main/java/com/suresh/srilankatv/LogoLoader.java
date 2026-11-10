package com.suresh.srilankatv;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.util.LruCache;
import android.view.Gravity;
import android.widget.Button;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Displays correctly matched channel logos from public logo metadata.
 * Unmatched entries keep a neutral TV placeholder instead of a guessed logo.
 * Downloads are performed off the UI thread and cached in memory.
 */
public final class LogoLoader {
    private LogoLoader() {}
    private static final ExecutorService IO = Executors.newFixedThreadPool(4);
    private static final LruCache<String, Bitmap> CACHE = new LruCache<String,Bitmap>(8192) {
        @Override protected int sizeOf(String key, Bitmap value) {
            return Math.max(1,value.getByteCount()/1024);
        }
    };

    private static void apply(Activity activity, Button button, String url, Bitmap image) {
        if (activity.isFinishing() || image == null || !url.equals(button.getTag())) return;
        int side = (int)(activity.getResources().getDisplayMetrics().density * 44 + 0.5f);
        BitmapDrawable drawable = new BitmapDrawable(activity.getResources(), image);
        drawable.setBounds(0,0,side,side);
        button.setCompoundDrawablePadding((int)(5 * activity.getResources().getDisplayMetrics().density));
        button.setCompoundDrawables(drawable,null,null,null);
        button.setGravity(Gravity.CENTER_VERTICAL | Gravity.LEFT);
    }

    public static void attach(Activity activity, Button button, String url) {
        if (url == null || !url.startsWith("https://")) return;
        button.setTag(url);
        Bitmap cached;
        synchronized (CACHE) { cached = CACHE.get(url); }
        if (cached != null) {
            apply(activity,button,url,cached);
            return;
        }
        IO.execute(() -> {
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection) new URL(url).openConnection();
                connection.setConnectTimeout(6000);
                connection.setReadTimeout(8000);
                connection.setRequestProperty("Accept", "image/png,image/jpeg,image/webp,image/*");
                if (connection.getResponseCode() != 200) return;
                String type = connection.getContentType();
                if (type == null || !type.toLowerCase().startsWith("image/")) return;
                ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                try (InputStream input = connection.getInputStream()) {
                    byte[] buffer = new byte[8192];
                    int n;
                    while ((n=input.read(buffer)) > 0) {
                        if (bytes.size()+n > 800_000) return;
                        bytes.write(buffer,0,n);
                    }
                }
                byte[] data = bytes.toByteArray();
                BitmapFactory.Options opts = new BitmapFactory.Options();
                opts.inJustDecodeBounds = true;
                BitmapFactory.decodeByteArray(data,0,data.length,opts);
                if (opts.outWidth <= 0 || opts.outHeight <= 0) return;
                int scale = 1;
                while (Math.max(opts.outWidth/scale,opts.outHeight/scale)>300) scale*=2;
                opts.inJustDecodeBounds = false;
                opts.inSampleSize = scale;
                Bitmap img=BitmapFactory.decodeByteArray(data,0,data.length,opts);
                if (img == null) return;
                synchronized (CACHE) { CACHE.put(url,img); }
                activity.runOnUiThread(() -> apply(activity,button,url,img));
            } catch (Exception ignored) {
                // A failed logo is cosmetic; never prevent channel selection.
            } finally {
                if (connection != null) connection.disconnect();
            }
        });
    }
}
