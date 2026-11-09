package lk.openstream.tv.independent;

import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.widget.Toast;
import lk.openstream.tv.common.Channel;
import lk.openstream.tv.common.TvMenuActivity;

public class MainActivity extends TvMenuActivity {
    @Override protected String appTitle(){return "OPENSTREAM  •  TV";}
    @Override protected String appSubtitle(){
        return "Independent player  •  Public stream candidates only  •  Other sources require broadcaster authorization";
    }
    @Override protected void openChannel(Channel ch) {
        if(ch.canPlayDirectly()) {
            Intent i=new Intent(this,PlayerActivity.class);
            i.putExtra("title",ch.name);i.putExtra("url",ch.url);
            startActivity(i);
            return;
        }
        new AlertDialog.Builder(this)
            .setTitle(ch.name)
            .setMessage("This channel's recorded source is not independently verified or is restricted to the original provider.\n\n" +
              "This independent app does not copy SLTV credentials, licence keys, or private server access.\n\n" +
              "Access category: "+ch.status())
            .setNegativeButton("Close",(d,w)->d.dismiss())
            .setPositiveButton("Open original SLTV",(d,w)->{
                Intent launch=getPackageManager().getLaunchIntentForPackage("com.sltv.app");
                if(launch!=null)startActivity(launch);
                else Toast.makeText(this,"Install and sign in to original SLTV first.",Toast.LENGTH_LONG).show();
            }).show();
    }
}
