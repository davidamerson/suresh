package lk.openstream.tv.independent;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.KeyEvent;
import android.widget.FrameLayout;
import android.widget.TextView;
import androidx.media3.common.MediaItem;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.ui.PlayerView;

public class PlayerActivity extends Activity {
    private ExoPlayer player;
    private TextView status;
    private String title;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_FULLSCREEN|View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        String uri=getIntent().getStringExtra("url");
        title=getIntent().getStringExtra("title");
        if(uri==null||!uri.startsWith("http")){finish();return;}
        FrameLayout root=new FrameLayout(this);root.setBackgroundColor(Color.BLACK);setContentView(root);
        PlayerView view=new PlayerView(this);
        view.setUseController(true);
        root.addView(view,new FrameLayout.LayoutParams(-1,-1));
        status=new TextView(this);status.setTextColor(Color.WHITE);status.setTextSize(16);
        status.setPadding(24,12,24,12);status.setBackgroundColor(Color.argb(185,0,0,0));
        FrameLayout.LayoutParams lp=new FrameLayout.LayoutParams(-1,-2,Gravity.TOP);
        root.addView(status,lp);
        status.setText(title+"  •  Connecting…");
        player=new ExoPlayer.Builder(this).build();
        view.setPlayer(player);
        player.addListener(new Player.Listener(){
            @Override public void onPlaybackStateChanged(int state){
                if(state==Player.STATE_READY)status.setText(title+"  •  Playing (Back to return)");
                if(state==Player.STATE_BUFFERING)status.setText(title+"  •  Buffering…");
                if(state==Player.STATE_ENDED)status.setText(title+"  •  Broadcast ended");
            }
            @Override public void onPlayerError(PlaybackException error){
                status.setText(title+"  •  Unable to play this stream.\n" +
                    "It may be unavailable, restricted, or require broadcaster credentials.\n" +
                    "Error code: "+error.errorCode+"   •  Back to choose another channel");
            }
        });
        player.setMediaItem(MediaItem.fromUri(uri));
        player.prepare();player.play();
    }
    @Override protected void onStop(){super.onStop(); if(player!=null){player.release();player=null;}}
}
