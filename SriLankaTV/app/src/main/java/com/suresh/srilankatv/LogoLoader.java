package com.suresh.srilankatv;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.util.LruCache;
import android.view.Gravity;
import android.widget.Button;

import java.io.InputStream;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;

/**
 * All channel icons are bundled locally with the APK. There are no
 * asynchronous logo HTTP requests or network-dependent UI updates.
 * Exact channel name and source address select the correct bundled image.
 */
public final class LogoLoader {
    private LogoLoader() {}
    private static final LruCache<String,Bitmap> CACHE = new LruCache<String,Bitmap>(16*1024) {
        @Override protected int sizeOf(String key, Bitmap value) {
            return Math.max(1,value.getByteCount()/1024);
        }
    };

    private static String path(String name,String url) {
        try {
            MessageDigest digest=MessageDigest.getInstance("SHA-256");
            byte[] data=digest.digest((name+String.valueOf((char)0)+url).getBytes(StandardCharsets.UTF_8));
            StringBuilder key=new StringBuilder();
            for (int i=0;i<12;i++) {
                key.append(Character.forDigit((data[i]>>>4)&15,16));
                key.append(Character.forDigit(data[i]&15,16));
            }
            return "logos/"+key+".png";
        } catch (Exception e) {
            return "";
        }
    }

    public static boolean attach(Activity activity, Button button,
                                 PlaylistStore.Channel channel) {
        String file=path(channel.name,channel.url);
        if (file.isEmpty()) return false;
        Bitmap image=CACHE.get(file);
        if (image==null) {
            try (InputStream stream=activity.getAssets().open(file)) {
                BitmapFactory.Options options = new BitmapFactory.Options();
                options.inPreferredConfig=Bitmap.Config.RGB_565;
                image=BitmapFactory.decodeStream(stream,null,options);
                if (image!=null) CACHE.put(file,image);
            } catch (Exception ignored) {
                return false;
            }
        }
        if (image==null) return false;
        BitmapDrawable drawable=new BitmapDrawable(activity.getResources(),image);
        float density=activity.getResources().getDisplayMetrics().density;
        int imageW=(int)(96*density+0.5f);
        int imageH=(int)(54*density+0.5f);
        drawable.setBounds(0,0,imageW,imageH);
        button.setCompoundDrawables(null,drawable,null,null);
        button.setCompoundDrawablePadding((int)(5*density));
        button.setGravity(Gravity.CENTER);
        return true;
    }
}
