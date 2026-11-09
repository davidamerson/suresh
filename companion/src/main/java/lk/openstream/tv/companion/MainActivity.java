package lk.openstream.tv.companion;

import android.app.AlertDialog;
import android.content.Intent;
import android.content.Context;
import android.provider.Settings;
import android.view.accessibility.AccessibilityManager;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.widget.Toast;
import java.util.List;
import lk.openstream.tv.common.Channel;
import lk.openstream.tv.common.TvMenuActivity;

public final class MainActivity extends TvMenuActivity {
    @Override protected String appTitle(){return "SLTV COMPANION  •  TV";}
    @Override protected String appSubtitle(){
        return "Uses the ORIGINAL SLTV app and its own streams and updates  •  Accessibility permission required";
    }
    private boolean enabled(){
        AccessibilityManager am=(AccessibilityManager)getSystemService(Context.ACCESSIBILITY_SERVICE);
        if(am==null)return false;
        List<AccessibilityServiceInfo> list=am.getEnabledAccessibilityServiceList(
            AccessibilityServiceInfo.FEEDBACK_ALL_MASK);
        for(AccessibilityServiceInfo i:list){
            if(i.getResolveInfo()!=null && i.getResolveInfo().serviceInfo!=null &&
               getPackageName().equals(i.getResolveInfo().serviceInfo.packageName))return true;
        }
        return false;
    }
    @Override protected void openChannel(Channel c){
        Intent intent=getPackageManager().getLaunchIntentForPackage("com.sltv.app");
        if(intent==null){
            new AlertDialog.Builder(this).setTitle("Original SLTV app is required")
                .setMessage("Install SLTV V1.4.8 from its developer, open it, and sign in normally. "+
                    "This companion cannot use SLTV's server or player unless the original app is installed.")
                .setPositiveButton("OK",(d,w)->d.dismiss()).show();return;
        }
        if(!enabled()){
            new AlertDialog.Builder(this).setTitle("Enable SLTV Companion navigation")
                .setMessage("To choose channels inside the ORIGINAL SLTV app, enable the "+
                    "'SLTV Companion channel navigation' Accessibility Service in Android Settings.\n\n"+
                    "It activates only for SLTV, only after you choose a channel, and does not read passwords.")
                .setNegativeButton("Cancel",(d,w)->d.dismiss())
                .setPositiveButton("Accessibility Settings",(d,w)->{
                    startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
                }).show();return;
        }
        getSharedPreferences("sltv_navigation",Context.MODE_PRIVATE).edit()
            .putString("target_channel",c.name).putLong("requested_at",System.currentTimeMillis()).apply();
        startActivity(intent);
        Toast.makeText(this,"Opening "+c.name+" inside SLTV…",Toast.LENGTH_SHORT).show();
    }
}
