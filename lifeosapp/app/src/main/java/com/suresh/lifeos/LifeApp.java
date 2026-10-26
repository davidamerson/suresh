package com.suresh.lifeos;
import android.app.*;import android.content.*;import android.os.*;
public class LifeApp extends Application {
 public static final String CH="lifeos_private";
 @Override public void onCreate(){super.onCreate(); if(Build.VERSION.SDK_INT>=26){NotificationChannel c=new NotificationChannel(CH,"Private Life OS reminders",NotificationManager.IMPORTANCE_HIGH);c.setDescription("Private task reminders");c.setLockscreenVisibility(android.app.Notification.VISIBILITY_SECRET);getSystemService(NotificationManager.class).createNotificationChannel(c);} Store.get(this); AlarmReceiver.scheduleToday(this);}
}
