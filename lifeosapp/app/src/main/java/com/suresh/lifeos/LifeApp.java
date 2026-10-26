package com.suresh.lifeos;
import android.app.*;import android.content.*;import android.os.*;
public class LifeApp extends Application {
 public static final String CH="lifeos_private";
 @Override public void onCreate(){super.onCreate();if(Build.VERSION.SDK_INT>=26){NotificationChannel c=new NotificationChannel(CH,"Private Life OS reminders",NotificationManager.IMPORTANCE_HIGH);c.setDescription("Private task reminders");c.setLockscreenVisibility(android.app.Notification.VISIBILITY_SECRET);getSystemService(NotificationManager.class).createNotificationChannel(c);}Store.get(this);AlarmReceiver.scheduleUpcoming(this);registerActivityLifecycleCallbacks(new ActivityLifecycleCallbacks(){public void onActivityCreated(Activity a,Bundle b){}public void onActivityStarted(Activity a){}public void onActivityResumed(Activity a){if(a instanceof MainActivity){MainActivity m=(MainActivity)a;if(!m.unlocked)m.showLock();}}public void onActivityPaused(Activity a){}public void onActivityStopped(Activity a){if(a instanceof MainActivity)((MainActivity)a).unlocked=false;}public void onActivitySaveInstanceState(Activity a,Bundle b){}public void onActivityDestroyed(Activity a){}});}
}
