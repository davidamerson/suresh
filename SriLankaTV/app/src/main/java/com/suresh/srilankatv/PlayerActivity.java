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
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.view.View;
import org.json.JSONObject;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.InputStream;
import java.io.ByteArrayOutputStream;

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
    private boolean currentWorker;
    private boolean attemptedDash;
    private Button normalFallbackButton;
    private int normalFallbackIndex = -1;
    private int requestedChannel = 0;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        setRequestedOrientation(BuildConfig.FLAVOR.equals("phone")
            ? ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED
            : ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
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
        normalFallbackButton = controlButton("Try normal stream (not HD)");
        normalFallbackButton.setVisibility(View.GONE);
        FrameLayout.LayoutParams normalParams = new FrameLayout.LayoutParams(
            dp(250), dp(56), Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        normalParams.bottomMargin = dp(76);
        root.addView(normalFallbackButton, normalParams);
        normalFallbackButton.setOnClickListener(v -> {
            if (normalFallbackIndex >= 0) play(normalFallbackIndex);
        });
        // Visible on-screen controls work with a mouse on TV and with touch on phones.
        // TV remotes can also use D-pad Up/Down, OK and Back.
        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        buttons.setGravity(Gravity.CENTER);
        buttons.setPadding(dp(5), dp(3), dp(5), dp(3));
        buttons.setBackgroundColor(Color.argb(205, 13, 22, 36));
        Button previous = controlButton("◀ Prev");
        Button pause = controlButton("Play/Pause");
        Button next = controlButton("Next ▶");
        Button back = controlButton("Back");
        buttons.addView(previous, new LinearLayout.LayoutParams(0, -1, 1f));
        buttons.addView(pause, new LinearLayout.LayoutParams(0, -1, 1f));
        buttons.addView(next, new LinearLayout.LayoutParams(0, -1, 1f));
        buttons.addView(back, new LinearLayout.LayoutParams(0, -1, 1f));
        FrameLayout.LayoutParams controlsLayout = new FrameLayout.LayoutParams(
            -1, dp(68), Gravity.BOTTOM);
        root.addView(buttons, controlsLayout);
        previous.setOnClickListener(v -> play(currentIndex - 1));
        next.setOnClickListener(v -> play(currentIndex + 1));
        pause.setOnClickListener(v -> {
            if (player != null) {
                if (player.isPlaying()) player.pause();
                else player.play();
            }
        });
        back.setOnClickListener(v -> finish());
        setContentView(root);

        player = new ExoPlayer.Builder(this).build();
        playerView.setPlayer(player);
        player.addListener(new Player.Listener() {
            @Override public void onPlayerError(PlaybackException error) {
                // No blind DASH retry: the SLTV worker path typically returns
                // JSON metadata, which is neither an HLS nor a DASH manifest.
                status.setText("Playback failed: " + error.errorCodeName + "\n"
                    + "This source may be unavailable or require provider authorization.\n"
                    + "Try a normal channel or return to the channel list.");
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

    private Button controlButton(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(BuildConfig.FLAVOR.equals("phone") ? 12 : 15);
        b.setAllCaps(false);
        b.setFocusable(true);
        b.setFocusableInTouchMode(true);
        return b;
    }

    private int dp(int v) {
        return (int)(v * getResources().getDisplayMetrics().density + .5f);
    }

    private static String nameKey(String name) {
        String n = name.toLowerCase(Locale.ROOT)
            .replace("\u200e", "").replace("\u200f", "").replace("²", "")
            .replaceAll("\\b(hd|sd|ultra|tv)\\b", "")
            .replaceAll("[^a-z0-9]", "");
        return n.replace("dearana", "derana")
                .replace("rupawahini", "rupavahini")
                .replace("swarnawahini", "swarnavahini");
    }

    private int findNormal(int selected) {
        String wanted = nameKey(channels.get(selected).name);
        if (wanted.isEmpty()) return -1;
        for (int i = 0; i < channels.size(); i++) {
            if (i == selected) continue;
            PlaylistStore.Channel c = channels.get(i);
            if (c.url.contains(".thundercat.workers.dev/")) continue;
            if (nameKey(c.name).equals(wanted)) return i;
        }
        return -1;
    }

    private void directPlay(String address, String mimeType) {
        MediaItem.Builder builder = new MediaItem.Builder().setUri(address);
        if (mimeType != null) builder.setMimeType(mimeType);
        player.setMediaItem(builder.build());
        player.prepare();
        player.play();
    }

    private void inspectWorker(String address, int requestId) {
        new Thread(() -> {
            HttpURLConnection conn = null;
            String outcome = null;
            String playableMime = null;
            try {
                conn = (HttpURLConnection)new URL(address).openConnection();
                conn.setConnectTimeout(7500);
                conn.setReadTimeout(7500);
                conn.setRequestProperty("Accept",
                    "application/json,application/vnd.apple.mpegurl,application/dash+xml,*/*");
                int statusCode=conn.getResponseCode();
                if (statusCode != 200 && statusCode != 206) {
                    outcome="SLTV server returned HTTP " + statusCode + ".\n"
                        + "Try a normal channel or use the original app.";
                } else {
                    String contentType=String.valueOf(conn.getContentType()).toLowerCase(Locale.ROOT);
                    if (contentType.contains("json")) {
                        // Read only public channel metadata. Do not save or reuse private
                        // licence proxies, signed URLs, access tokens or subscriber details.
                        ByteArrayOutputStream buf = new ByteArrayOutputStream();
                        try (InputStream stream=conn.getInputStream()) {
                            byte[] chunk=new byte[4096]; int read;
                            while ((read=stream.read(chunk))>0 && buf.size()<15000) {
                                buf.write(chunk,0,Math.min(read,15000-buf.size()));
                            }
                        }
                        JSONObject root=new JSONObject(buf.toString("UTF-8"));
                        JSONObject data=root.optJSONObject("data");
                        JSONObject drm=data==null?null:data.optJSONObject("drm");
                        if (drm!=null && (drm.optBoolean("widevine")
                            || drm.optBoolean("verimatrix") || drm.optBoolean("fairplay"))) {
                            outcome="This HD stream requires authorized DRM playback.\n"
                                + "SLTV's JSON response is not a video playlist.\n"
                                + "Try the normal stream below, or use the original SLTV app for authorized HD.";
                        } else {
                            outcome="This SLTV route supplies JSON metadata, not a direct video playlist.\n"
                                + "Try the normal stream or use the original SLTV app.";
                        }
                    } else if (contentType.contains("mpegurl")) {
                        playableMime=MimeTypes.APPLICATION_M3U8;
                    } else if (contentType.contains("dash+xml")) {
                        playableMime=MimeTypes.APPLICATION_MPD;
                    } else {
                        outcome="This SLTV route did not return a supported public HLS/DASH playlist.\n"
                            + "Try a normal channel.";
                    }
                }
            } catch (Exception e) {
                outcome="Could not read this SLTV route (" + e.getClass().getSimpleName()
                    + "). Try a normal channel.";
            } finally {
                if (conn != null) conn.disconnect();
            }
            final String result=outcome;
            final String mime=playableMime;
            runOnUiThread(() -> {
                if (requestedChannel != requestId || isFinishing()) return;
                if (mime!=null) directPlay(address,mime);
                else status.setText(result);
            });
        },"sltv-public-metadata-check").start();
    }

    private void play(int index) {
        if (channels == null || channels.isEmpty()) return;
        requestedChannel++;
        int requestId=requestedChannel;
        currentIndex=(index % channels.size() + channels.size()) % channels.size();
        PlaylistStore.Channel channel=channels.get(currentIndex);
        channelTitle.setText(channel.name + "    (" + (currentIndex + 1)
                + "/" + channels.size() + ")");
        status.setText("Connecting to channel…");
        player.stop();
        player.clearMediaItems();
        currentWorker=channel.url.contains(".thundercat.workers.dev/");
        normalFallbackIndex=currentWorker ? findNormal(currentIndex) : -1;
        normalFallbackButton.setVisibility(normalFallbackIndex < 0 ? View.GONE : View.VISIBLE);
        if (currentWorker) {
            inspectWorker(channel.url,requestId);
            return;
        }
        String path=channel.url.toLowerCase(Locale.ROOT).split("\\?")[0];
        String mime=path.endsWith(".m3u8") ? MimeTypes.APPLICATION_M3U8
            : (path.endsWith(".mpd") ? MimeTypes.APPLICATION_MPD : null);
        directPlay(channel.url,mime);
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
