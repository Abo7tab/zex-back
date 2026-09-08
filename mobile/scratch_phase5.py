import os

base_dir = r"C:\Users\moham\OneDrive\Desktop\z\mobile\zex-app\app\src\main"
pkg = os.path.join(base_dir, "java", "com", "zex", "tracker")

def write_file(path, content):
    full_path = os.path.join(pkg, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        content = content.replace(r"\${", "${").replace(r"\$", "$")
        f.write(content.strip() + "\n")

# 1. Proguard Rules
proguard_path = r"C:\Users\moham\OneDrive\Desktop\z\mobile\zex-app\app\proguard-rules.pro"
proguard = """
-keepattributes *Annotation*, Signature, InnerClasses, EnclosingMethod
-keep class com.zex.tracker.data.remote.dto.** { *; }
-keep class com.zex.tracker.domain.model.** { *; }
-keep class com.zex.tracker.core.constants.** { *; }
-keep class * extends androidx.room.RoomDatabase
-keep @androidx.room.Entity class *
-keep class * implements okhttp3.Interceptor { *; }
-keep class retrofit2.** { *; }
-keep class com.google.firebase.** { *; }
"""
with open(proguard_path, "a") as f:
    f.write("\n" + proguard + "\n")

# 2. NetworkModule (Redact tokens & Use ZexExtendedApi)
write_file("di/NetworkModule.kt", r"""
package com.zex.tracker.di

import com.zex.tracker.BuildConfig
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.data.remote.api.ZexExtendedApi
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideAuthInterceptor(securePrefs: SecurePrefs): Interceptor {
        return Interceptor { chain ->
            val original = chain.request()
            val builder = original.newBuilder()
            
            val ownerToken = securePrefs.getString(ZexConstants.KEY_OWNER_TOKEN)
            if (!ownerToken.isNullOrEmpty()) {
                builder.header(ZexConstants.HEADER_AUTHORIZATION, "Bearer $ownerToken")
            }
            
            val deviceToken = securePrefs.getString(ZexConstants.KEY_DEVICE_TOKEN)
            if (!deviceToken.isNullOrEmpty()) {
                builder.header(ZexConstants.HEADER_DEVICE_TOKEN, deviceToken)
            }
            
            builder.header("Accept", "application/json")
            chain.proceed(builder.build())
        }
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(authInterceptor: Interceptor): OkHttpClient {
        val logging = HttpLoggingInterceptor { message ->
            ZexLogger.d("OkHttp", message)
        }.apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY else HttpLoggingInterceptor.Level.NONE
            redactHeader(ZexConstants.HEADER_AUTHORIZATION)
            redactHeader(ZexConstants.HEADER_DEVICE_TOKEN)
        }

        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .writeTimeout(20, TimeUnit.SECONDS)
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    @Provides
    @Singleton
    fun provideZexApi(retrofit: Retrofit): ZexExtendedApi {
        return retrofit.create(ZexExtendedApi::class.java)
    }
}
""")

# 3. LocationTracker (Handle Permission Denied Gracefully)
write_file("security/location/LocationTracker.kt", r"""
package com.zex.tracker.security.location

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.os.Looper
import androidx.core.app.ActivityCompat
import com.google.android.gms.location.*
import com.zex.tracker.core.logging.ZexLogger
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.tasks.await
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LocationTracker @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val fusedLocationClient: FusedLocationProviderClient = 
        LocationServices.getFusedLocationProviderClient(context)
    
    private var locationCallback: LocationCallback? = null

    @SuppressLint("MissingPermission")
    suspend fun getCurrentLocation(): Location? {
        if (!hasLocationPermission()) {
            ZexLogger.w("LocationTracker", "Location permission denied. Failing gracefully.")
            return null
        }
        return try {
            fusedLocationClient.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, null).await()
        } catch (e: Exception) {
            ZexLogger.e("LocationTracker", "Failed to get location", e)
            null
        }
    }

    @SuppressLint("MissingPermission")
    fun startContinuous(intervalMs: Long, onLocation: (Location) -> Unit) {
        if (!hasLocationPermission()) {
            ZexLogger.w("LocationTracker", "Location permission denied. Cannot start continuous.")
            return
        }
        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, intervalMs)
            .setMinUpdateIntervalMillis(intervalMs / 2)
            .build()

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                result.lastLocation?.let(onLocation)
            }
        }

        fusedLocationClient.requestLocationUpdates(request, locationCallback!!, Looper.getMainLooper())
        ZexLogger.i("LocationTracker", "Started continuous tracking at \${intervalMs}ms")
    }

    fun stopContinuous() {
        locationCallback?.let { fusedLocationClient.removeLocationUpdates(it) }
        locationCallback = null
        ZexLogger.i("LocationTracker", "Stopped continuous tracking")
    }
    
    private fun hasLocationPermission(): Boolean {
        return ActivityCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
               ActivityCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
    }
}
""")

# 4. CommandProcessor (Found Mode clears everything)
write_file("service/CommandProcessor.kt", r"""
package com.zex.tracker.service

import android.content.Context
import android.content.Intent
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.data.repository.DeviceRepository
import com.zex.tracker.domain.model.Command
import com.zex.tracker.domain.model.CommandType
import com.zex.tracker.security.LockManager
import com.zex.tracker.security.NetworkForcer
import com.zex.tracker.security.SearchModeManager
import com.zex.tracker.security.ScreamManager
import com.zex.tracker.security.location.LocationTracker
import com.zex.tracker.ui.screens.scream.ScreamActivity
import com.zex.tracker.ui.screens.lock.LockActivity
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CommandProcessor @Inject constructor(
    @ApplicationContext private val context: Context,
    private val locationTracker: LocationTracker,
    private val deviceRepo: DeviceRepository,
    private val networkForcer: NetworkForcer,
    private val screamManager: ScreamManager,
    private val lockManager: LockManager,
    private val searchModeManager: SearchModeManager,
    private val prefs: SecurePrefs,
    private val serviceController: ServiceController
) {
    private val scope = CoroutineScope(Dispatchers.IO)

    fun process(command: Command) {
        ZexLogger.i("CommandProcessor", "Processing command: \${command.type}")
        scope.launch {
            try {
                when (command.type) {
                    CommandType.LOCATE -> handleLocate()
                    CommandType.CONTINUOUS_TRACK -> {
                        val interval = command.parameters?.get("interval")?.toIntOrNull() ?: 30
                        searchModeManager.enterSearchMode("command_track", interval)
                    }
                    CommandType.STOP_TRACKING -> searchModeManager.exitSearchMode("command_stop")
                    CommandType.SCREAM -> handleScream()
                    CommandType.STOP_SCREAM -> handleStopScream()
                    CommandType.LOCK -> handleLock()
                    CommandType.ENABLE_NET -> networkForcer.forceNetwork()
                    CommandType.STOLEN_MODE -> {
                        prefs.putBoolean("isStolen", true)
                        ServiceController.isStolen = true
                        searchModeManager.enterSearchMode("stolen_mode", 30)
                    }
                    CommandType.FOUND_MODE -> {
                        prefs.putBoolean("isStolen", false)
                        ServiceController.isStolen = false
                        searchModeManager.exitSearchMode("found_mode")
                        handleStopScream()
                    }
                    CommandType.STATUS -> handleStatus()
                    CommandType.PHOTO -> ZexLogger.w("CommandProcessor", "PHOTO ignored by rule")
                }
                deviceRepo.sendCommandResponse(command.id, "EXECUTED")
            } catch (e: Exception) {
                ZexLogger.e("CommandProcessor", "Failed executing \${command.type}", e)
                deviceRepo.sendCommandResponse(command.id, "FAILED")
            }
        }
    }

    private suspend fun handleLocate() {
        val loc = locationTracker.getCurrentLocation()
        if (loc != null) deviceRepo.sendLocation(loc)
    }

    private fun handleScream() {
        ServiceController.isScreaming = true
        val intent = Intent(context, ScreamActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
        context.startActivity(intent)
    }

    private fun handleStopScream() {
        ServiceController.isScreaming = false
        screamManager.stopScream()
        // Broadcast to close ScreamActivity if open
        context.sendBroadcast(Intent("com.zex.tracker.STOP_SCREAM"))
    }

    private fun handleLock() {
        if (lockManager.isDeviceAdminActive()) {
            lockManager.lockNow()
        } else {
            val intent = Intent(context, LockActivity::class.java).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            }
            context.startActivity(intent)
        }
    }

    private suspend fun handleStatus() {
        searchModeManager.checkOwnerSearching()
        handleLocate()
    }
}
""")

# 5. DashboardScreen (Added Screaming Chip)
write_file("ui/screens/dashboard/DashboardScreen.kt", r"""
package com.zex.tracker.ui.screens.dashboard

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.service.ServiceController
import com.zex.tracker.ui.components.PrimaryButton

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(prefs: SecurePrefs) {
    val uid = prefs.getString(ZexConstants.KEY_DEVICE_UID) ?: "Unknown UID"
    val context = LocalContext.current
    
    // Auto refresh trigger
    var trigger by remember { mutableIntStateOf(0) }

    Column(modifier = Modifier.fillMaxSize().padding(24.dp)) {
        Text("ZEX Dashboard", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(16.dp))
        
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (ServiceController.isStolen) {
                FilterChip(selected = true, onClick = {}, label = { Text("Stolen") }, colors = FilterChipDefaults.filterChipColors(selectedContainerColor = MaterialTheme.colorScheme.errorContainer))
            }
            if (ServiceController.isSearching) {
                FilterChip(selected = true, onClick = {}, label = { Text("Searching") }, colors = FilterChipDefaults.filterChipColors(selectedContainerColor = MaterialTheme.colorScheme.primaryContainer))
            }
            if (ServiceController.isScreaming) {
                FilterChip(selected = true, onClick = {}, label = { Text("Screaming") }, colors = FilterChipDefaults.filterChipColors(selectedContainerColor = MaterialTheme.colorScheme.error))
            }
            if (!ServiceController.isStolen && !ServiceController.isSearching && !ServiceController.isScreaming) {
                FilterChip(selected = true, onClick = {}, label = { Text("Normal") })
            }
        }
        
        Spacer(Modifier.height(16.dp))
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Device UID: \${uid}")
                Text("Tracking: \${ServiceController.isTracking}")
                Text("Interval: \${ServiceController.trackingInterval / 1000}s")
                Text("Last Check: \${prefs.getLong("lastSearchCheckAt", 0L)}")
            }
        }
        Spacer(Modifier.height(24.dp))
        PrimaryButton(
            text = "Start Protection Service",
            onClick = {
                ServiceController(context).startProtection()
                trigger++
            }
        )
        Spacer(Modifier.height(8.dp))
        PrimaryButton(
            text = "Stop Protection Service",
            onClick = {
                ServiceController(context).stopProtection()
                trigger++
            }
        )
        Spacer(Modifier.height(8.dp))
        PrimaryButton(
            text = "Refresh UI Status",
            onClick = { trigger++ }
        )
    }
}
""")

# 6. TEST_CHECKLIST.md
docs_dir = r"C:\Users\moham\OneDrive\Desktop\z\mobile\zex-app\docs"
os.makedirs(docs_dir, exist_ok=True)
with open(os.path.join(docs_dir, "TEST_CHECKLIST.md"), "w", encoding="utf-8") as f:
    f.write("""
# ZEX Mobile - Test Checklist

## 1. Setup & Auth
- [ ] Install APK on a physical Android device.
- [ ] Open App -> Welcome Screen -> Create Account (or Login).
- [ ] Provide Name, Email, Phone, Password, and PIN code.
- [ ] Device automatically registers and saves UID/Token.
- [ ] Verify Dashboard UI loads correctly with the correct Device UID.

## 2. Protection Service
- [ ] Click "Start Protection Service".
- [ ] Grant location permissions.
- [ ] Grant Device Admin (if prompted for LOCK).
- [ ] Verify "ZEX Protection active" notification appears and cannot be swiped away.

## 3. Web/Backend Interaction
- [ ] Login to the Web Portal with the same account.
- [ ] Send `LOCATE` command. Wait for coordinates to update on the map.
- [ ] Send `SEARCH MODE`. Check device notification updates to "Search mode active".
- [ ] Verify Dashboard UI shows "Searching" chip.
- [ ] Send `STOP SEARCH`. Verify device returns to normal.
- [ ] Send `SCREAM`. Verify phone loudly alarms, vibrates, shows red overlay.
- [ ] Send `STOP SCREAM`. Verify phone silences.
- [ ] Send `STOLEN MODE`. Verify device enters frequent tracking mode and stolen UI chip appears.
- [ ] Send `FOUND MODE`. Verify device completely exits stolen mode and returns to normal.

## 4. Edge Cases & Offline
- [ ] Reboot the phone. Verify the Foreground Service restarts automatically within 1-2 minutes.
- [ ] Toggle Wi-Fi OFF and send `SEARCH MODE` via web (won't arrive immediately).
- [ ] Send SMS command `#ZEX#SEARCH_ON` from the owner's phone number to the target device.
- [ ] Verify the device forces network ON (if OS allows) and enters Search Mode.
- [ ] Deny Location permission manually in Android Settings. Wait 1 hour. Verify app does not crash, logs warning, and continues to heartbeat.

## 5. Security Validation
- [ ] Open Logcat and filter by `OkHttp`. Verify no sensitive Bearer tokens or X-Device-Tokens are printed.
- [ ] Export `app-debug.apk` and run it through `apkanalyzer`. Verify ProGuard rules successfully kept Retrofit models.
    """)
