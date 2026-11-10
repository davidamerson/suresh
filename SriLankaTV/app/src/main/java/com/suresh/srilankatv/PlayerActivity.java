package com.suresh.srilankatv;

import android.app.Activity;
import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.util.Log;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.TextView;
import androidx.media3.common.MediaItem;
import androidx.media3.common.MimeTypes;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.ui.PlayerView;
import androidx.media3.ui.AspectRatioFrameLayout;

import java.util.List;
import java.util.Locale;

/** Immersive, no playback buttons. Up=previous, down=next, Back=channel grid. */
public final class PlayerActivity extends Activity {
    private List<PlaylistStore.Channel> channels;
    private ExoPlayer exoPlayer;
    private PlayerView view;
    private TextView overlay;
    private TextView message;
    private int index;
    private int serial=0;
    private final Handler main=new Handler(Looper.getMainLooper());
    private Runnable hideOverlay;

    private int dp(float v){return (int)(v*getResources().getDisplayMetrics().density+.5f);}

    private void immersive(){
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION |
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON |
            WindowManager.LayoutParams.FLAG_FULLSCREEN);
        immersive();
        channels=PlaylistStore.getChannels(this);
        if(channels.size()!=22){finish();return;}
        FrameLayout root=new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);
        view=new PlayerView(this);
        view.setUseController(false);
        view.setResizeMode(AspectRatioFrameLayout.RESIZE_MODE_FIT);
        view.setFocusable(false);
        root.addView(view,new FrameLayout.LayoutParams(-1,-1));

        overlay=new TextView(this);
        overlay.setTextSize(21);
        overlay.setTextColor(Color.WHITE);
        overlay.setTypeface(null,1);
        overlay.setPadding(dp(20),dp(11),dp(20),dp(11));
        overlay.setBackgroundColor(0xB9091A29);
        FrameLayout.LayoutParams titleP=new FrameLayout.LayoutParams(-2,-2,
            Gravity.TOP|Gravity.LEFT);
        titleP.setMargins(dp(24),dp(20),0,0);
        root.addView(overlay,titleP);

        message=new TextView(this);
        message.setTextSize(21);
        message.setTextColor(0xFFE7F0F8);
        message.setGravity(Gravity.CENTER);
        message.setPadding(dp(35),dp(23),dp(35),dp(23));
        message.setBackgroundColor(0xBD091624);
        message.setVisibility(View.GONE);
        FrameLayout.LayoutParams messageP=new FrameLayout.LayoutParams(dp(650),-2,
            Gravity.CENTER);
        root.addView(message,messageP);
        setContentView(root);

        exoPlayer=new ExoPlayer.Builder(this).build();
        view.setPlayer(exoPlayer);
        exoPlayer.addListener(new Player.Listener(){
            @Override public void onPlayerError(PlaybackException e){
                message.setText("This stream could not be played.\n"
                    + "Check the connection or stream availability.\n"
                    + "UP / DOWN: change channel   •   BACK: channel list");
                message.setVisibility(View.VISIBLE);
            }
            @Override public void onPlaybackStateChanged(int state){
                if(state==Player.STATE_READY) message.setVisibility(View.GONE);
            }
        });
        index=Math.max(0,Math.min(21,getIntent().getIntExtra("channel_index",0)));
        tune(index);
    }

    private void showTemporaryTitle(String title) {
        overlay.setVisibility(View.VISIBLE);
        overlay.setText(title);
        if(hideOverlay!=null)main.removeCallbacks(hideOverlay);
        hideOverlay=()->overlay.setVisibility(View.GONE);
        main.postDelayed(hideOverlay,1900);
    }

    private void tune(int wanted) {
        if(channels==null || channels.isEmpty())return;
        index=(wanted+channels.size())%channels.size();
        Log.i("TV_CHANNEL","SELECT "+(index+1)+" "+channels.get(index).name);
        final PlaylistStore.Channel channel=channels.get(index);
        final int thisSerial=++serial;
        exoPlayer.stop();
        exoPlayer.clearMediaItems();
        message.setVisibility(View.GONE);
        showTemporaryTitle(String.format(Locale.ROOT,"%02d  %s",index+1,channel.name));
        if(channel.url.contains(".thundercat.workers.dev/")){
            // This endpoint advertises Widevine licensing. Never treat the
            // JSON response as an HLS or DASH video manifest.
            message.setText(channel.name+"\n\n"
                +"The SLTV source uses protected playback requiring a provider licence.\n"
                +"Use the authorized original SLTV application for this channel.\n\n"
                +"UP / DOWN: change channel    •    BACK: channel list");
            message.setVisibility(View.VISIBLE);
            return;
        }
        MediaItem.Builder item=new MediaItem.Builder().setUri(channel.url);
        String p=channel.url.toLowerCase(Locale.ROOT).split("\\?")[0];
        if(p.endsWith(".m3u8"))item.setMimeType(MimeTypes.APPLICATION_M3U8);
        if(p.endsWith(".mpd"))item.setMimeType(MimeTypes.APPLICATION_MPD);
        exoPlayer.setMediaItem(item.build());
        exoPlayer.prepare();
        exoPlayer.play();
    }

    @Override public boolean onKeyDown(int code,KeyEvent event) {
        switch(code) {
          case KeyEvent.KEYCODE_DPAD_UP:
          case KeyEvent.KEYCODE_CHANNEL_UP:
              tune(index-1);return true;
          case KeyEvent.KEYCODE_DPAD_DOWN:
          case KeyEvent.KEYCODE_CHANNEL_DOWN:
              tune(index+1);return true;
          case KeyEvent.KEYCODE_BACK:
              finish();return true;
          case KeyEvent.KEYCODE_DPAD_CENTER:
          case KeyEvent.KEYCODE_ENTER:
          case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
              if(exoPlayer!=null && exoPlayer.getMediaItemCount()>0){
                  if(exoPlayer.isPlaying())exoPlayer.pause();
                  else exoPlayer.play();
              }
              return true;
        }
        return super.onKeyDown(code,event);
    }

    @Override public void onBackPressed() { finish(); }

    @Override public void onWindowFocusChanged(boolean focus){
        super.onWindowFocusChanged(focus);
        if(focus)immersive();
    }

    @Override protected void onDestroy() {
        if(hideOverlay!=null)main.removeCallbacks(hideOverlay);
        if(view!=null)view.setPlayer(null);
        if(exoPlayer!=null)exoPlayer.release();
        super.onDestroy();
    }
}
