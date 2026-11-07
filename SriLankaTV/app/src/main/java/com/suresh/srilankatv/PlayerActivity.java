package com.suresh.srilankatv;

import android.app.Activity;
import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.Window;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.TextView;

import androidx.annotation.OptIn;
import androidx.media3.common.MediaItem;
import androidx.media3.common.MimeTypes;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.common.util.UnstableApi;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.ui.PlayerView;

import java.util.List;
import java.util.Locale;

public final class PlayerActivity extends Activity {
    private ExoPlayer player;
    private PlayerView playerView;
    private TextView channelTitle;
    private TextView status;
    private List<PlaylistStore.Channel> channels;
    private int currentIndex;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN |
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().getDecorView().setSystemUiVisibility(
            4 | 1024 | 4096 | 2);
        channels = PlaylistStore.getChannels(this);
        if (channels.isEmpty()) { finish(); return; }
        currentIndex = Math.max(0, Math.min(
            getIntent().getIntExtra("channel_index", 0), channels.size() - 1));

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);
        playerView = new PlayerView(this);
        playerView.setUseController(false);
        playerView.setFocusable(true);
        root.addView(playerView, new FrameLayout.LayoutParams(-1, -1));

        channelTitle = new TextView(this);
        channelTitle.setTextSize(23);
        channelTitle.setTextColor(Color.WHITE);
        channelTitle.setShadowLayer(3f, 1f, 2f, Color.BLACK);
        channelTitle.setPadding(dp(24), dp(12), dp(24), dp(12));
        FrameLayout.LayoutParams titleParams = new FrameLayout.LayoutParams(-2, -2,
                Gravity.TOP | Gravity.LEFT);
        root.addView(channelTitle, titleParams);

        status = new TextView(this);
        status.setTextColor(Color.WHITE);
        status.setTextSize(17);
        status.setPadding(dp(20), dp(14), dp(20), dp(14));
        status.setGravity(Gravity.CENTER);
        FrameLayout.LayoutParams statusParams = new FrameLayout.LayoutParams(
                -1, -2, Gravity.CENTER);
        root.addView(status, statusParams);
        setContentView(root);

        player = new ExoPlayer.Builder(this).build();
        playerView.setPlayer(player);
        player.addListener(new Player.Listener() {
            @Override public void onPlayerError(PlaybackException error) {
                status.setText("Unable to play this source.\n"
                    + "Up/Down: next channel   •   Back: channel list");
            }
            @Override public void onPlaybackStateChanged(int state) {
                if (state == Player.STATE_READY) {
                    status.setText("");
                } else if (state == Player.STATE_BUFFERING) {
                    status.setText("Connecting to channel…");
                }
            }
        });
        play(currentIndex);
    }

    private int dp(int v) {
        return (int)(v * getResources().getDisplayMetrics().density + .5f);
    }

    private void play(int index) {
        if (channels == null || channels.isEmpty()) return;
        currentIndex = (index % channels.size() + channels.size()) % channels.size();
        PlaylistStore.Channel channel = channels.get(currentIndex);
        channelTitle.setText(channel.name + "    (" + (currentIndex + 1)
                + "/" + channels.size() + ")");
        status.setText("Connecting to channel…");
        MediaItem.Builder builder = new MediaItem.Builder().setUri(channel.url);
        String path = channel.url.toLowerCase(Locale.ROOT).split("\\?")[0];
        if (path.endsWith(".m3u8")) builder.setMimeType(MimeTypes.APPLICATION_M3U8);
        else if (path.endsWith(".mpd")) builder.setMimeType(MimeTypes.APPLICATION_MPD);
        player.setMediaItem(builder.build());
        player.prepare();
        player.play();
    }

    @Override public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_DPAD_DOWN) {
            play(currentIndex + 1); return true;
        }
        if (keyCode == KeyEvent.KEYCODE_DPAD_UP) {
            play(currentIndex - 1); return true;
        }
        if (keyCode == KeyEvent.KEYCODE_DPAD_CENTER
                || keyCode == KeyEvent.KEYCODE_ENTER
                || keyCode == KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE) {
            if (player != null) {
                if (player.isPlaying()) player.pause(); else player.play();
                return true;
            }
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override protected void onStop() {
        super.onStop();
        if (player != null) player.pause();
    }

    @Override protected void onDestroy() {
        if (playerView != null) playerView.setPlayer(null);
        if (player != null) player.release();
        super.onDestroy();
    }
}
