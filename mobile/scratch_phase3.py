import os

base_dir = r"C:\Users\moham\OneDrive\Desktop\z\mobile\zex-app\app\src\main"
pkg = os.path.join(base_dir, "java", "com", "zex", "tracker")

def write_file(path, content):
    full_path = os.path.join(pkg, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

# ==========================================
# 1) Domain Models
# ==========================================
write_file("domain/model/CommandModels.kt", """
package com.zex.tracker.domain.model

enum class CommandType {
    LOCATE, CONTINUOUS_TRACK, STOP_TRACKING, SCREAM, STOP_SCREAM,
    LOCK, ENABLE_NET, STATUS, STOLEN_MODE, FOUND_MODE, PHOTO
}

enum class CommandStatus {
    PENDING, SENT, EXECUTED, FAILED
}

data class Command(
    val id: Int,
    val type: CommandType,
    val parameters: Map<String, String>? = null,
    val status: CommandStatus = CommandStatus.PENDING
)
""")

# ==========================================
# 2) Room Offline Buffer
# ==========================================
write_file("data/local/entity/LocationEntity.kt", """
package com.zex.tracker.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "locations")
data class LocationEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float,
    val altitude: Double,
    val speed: Float,
    val bearing: Float,
    val provider: String,
    val batteryLevel: Int,
    val networkType: String,
    val recordedAt: Long,
    val uploaded: Boolean = false
)
""")

write_file("data/local/dao/LocationDao.kt", """
package com.zex.tracker.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import com.zex.tracker.data.local.entity.LocationEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface LocationDao {
    @Insert
    suspend fun insert(location: LocationEntity): Long

    @Query("SELECT * FROM locations WHERE uploaded = 0 ORDER BY recordedAt ASC LIMIT :limit")
    suspend fun getPendingUploads(limit: Int): List<LocationEntity>

    @Query("UPDATE locations SET uploaded = 1 WHERE id IN (:ids)")
    suspend fun markUploaded(ids: List<Int>)

    @Query("DELETE FROM locations WHERE uploaded = 1 AND recordedAt < :timestamp")
    suspend fun deleteUploadedOlderThan(timestamp: Long)

    @Query("SELECT COUNT(*) FROM locations WHERE uploaded = 0")
    fun getPendingCountFlow(): Flow<Int>
}
""")

write_file("data/local/ZexDatabase.kt", """
package com.zex.tracker.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.zex.tracker.data.local.dao.LocationDao
import com.zex.tracker.data.local.entity.LocationEntity

@Database(entities = [LocationEntity::class], version = 1, exportSchema = false)
abstract class ZexDatabase : RoomDatabase() {
    abstract fun locationDao(): LocationDao
}
""")

write_file("di/DatabaseModule.kt", """
package com.zex.tracker.di

import android.content.Context
import androidx.room.Room
import com.zex.tracker.data.local.ZexDatabase
import com.zex.tracker.data.local.dao.LocationDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): ZexDatabase {
        return Room.databaseBuilder(context, ZexDatabase::class.java, "zex.db")
            .fallbackToDestructiveMigration()
            .build()
    }

    @Provides
    fun provideLocationDao(database: ZexDatabase): LocationDao {
        return database.locationDao()
    }
}
""")

# ==========================================
# 3) Utilities (Network, Battery, Location)
# ==========================================
write_file("core/utils/BatteryUtils.kt", """
package com.zex.tracker.core.utils

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager

object BatteryUtils {
    fun getBatteryLevel(context: Context): Int {
        val batteryStatus: Intent? = IntentFilter(Intent.ACTION_BATTERY_CHANGED).let { ifilter ->
            context.registerReceiver(null, ifilter)
        }
        val level: Int = batteryStatus?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale: Int = batteryStatus?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        return if (level == -1 || scale == -1) 50 else (level * 100 / scale.toFloat()).toInt()
    }
}
""")

write_file("core/utils/NetworkUtils.kt", """
package com.zex.tracker.core.utils

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities

object NetworkUtils {
    fun getNetworkType(context: Context): String {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val activeNetwork = cm.activeNetwork ?: return "NONE"
        val caps = cm.getNetworkCapabilities(activeNetwork) ?: return "NONE"
        
        return when {
            caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "WIFI"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "CELLULAR"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) -> "ETHERNET"
            else -> "UNKNOWN"
        }
    }
}
""")

write_file("security/location/LocationTracker.kt", """
package com.zex.tracker.security.location

import android.annotation.SuppressLint
import android.content.Context
import android.location.Location
import android.location.LocationManager
import android.os.Looper
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
    private val fusedLocationClient = LocationServices.getFusedLocationProviderClient(context)
    private val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    private var locationCallback: LocationCallback? = null

    @SuppressLint("MissingPermission")
    suspend fun getCurrentLocation(): Location? {
        return try {
            val location = fusedLocationClient.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, null).await()
            if (location != null) {
                ZexLogger.d("LocationTracker", "Fused location: \${location.provider} - acc: \${location.accuracy}")
                location
            } else {
                fallbackLocation()
            }
        } catch (e: Exception) {
            ZexLogger.e("LocationTracker", "Fused location failed", e)
            fallbackLocation()
        }
    }

    @SuppressLint("MissingPermission")
    private fun fallbackLocation(): Location? {
        return try {
            val providers = locationManager.getProviders(true)
            var bestLocation: Location? = null
            for (provider in providers) {
                val l = locationManager.getLastKnownLocation(provider) ?: continue
                if (bestLocation == null || l.accuracy < bestLocation.accuracy) {
                    bestLocation = l
                }
            }
            if (bestLocation != null) {
                ZexLogger.d("LocationTracker", "Fallback location: \${bestLocation.provider} - acc: \${bestLocation.accuracy}")
            }
            bestLocation
        } catch (e: Exception) {
            ZexLogger.e("LocationTracker", "Fallback location failed", e)
            null
        }
    }

    @SuppressLint("MissingPermission")
    fun startContinuous(intervalMs: Long, onLocation: (Location) -> Unit) {
        stopContinuous()
        try {
            val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, intervalMs).build()
            locationCallback = object : LocationCallback() {
                override fun onLocationResult(result: LocationResult) {
                    result.lastLocation?.let { onLocation(it) }
                }
            }
            fusedLocationClient.requestLocationUpdates(request, locationCallback!!, Looper.getMainLooper())
            ZexLogger.i("LocationTracker", "Continuous tracking started (\${intervalMs}ms)")
        } catch (e: Exception) {
            ZexLogger.e("LocationTracker", "Failed to start continuous tracking", e)
        }
    }

    fun stopContinuous() {
        locationCallback?.let {
            fusedLocationClient.removeLocationUpdates(it)
            locationCallback = null
            ZexLogger.i("LocationTracker", "Continuous tracking stopped")
        }
    }
}
""")

# ==========================================
# 4) Network Forcer
# ==========================================
write_file("security/NetworkForcer.kt", """
package com.zex.tracker.security

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkRequest
import android.net.NetworkCapabilities
import android.net.wifi.WifiManager
import android.os.Build
import com.zex.tracker.core.logging.ZexLogger
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class NetworkForcer @Inject constructor(@ApplicationContext private val context: Context) {
    fun forceNetwork() {
        try {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
                val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
                if (wifiManager?.isWifiEnabled == false) {
                    wifiManager.isWifiEnabled = true
                    ZexLogger.i("NetworkForcer", "Enabled WiFi via legacy API")
                }
            } else {
                ZexLogger.w("NetworkForcer", "Cannot force WiFi on Android 10+. Requesting via ConnectivityManager.")
                val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
                val request = NetworkRequest.Builder()
                    .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                    .build()
                cm.requestNetwork(request, object : ConnectivityManager.NetworkCallback() {})
            }
        } catch (e: Exception) {
            ZexLogger.e("NetworkForcer", "Failed to force network", e)
        }
    }
}
""")

# ==========================================
# 5) Command Processor
# ==========================================
write_file("service/CommandProcessor.kt", """
package com.zex.tracker.service

import android.content.Context
import android.content.Intent
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.repository.DeviceRepository
import com.zex.tracker.domain.model.Command
import com.zex.tracker.domain.model.CommandType
import com.zex.tracker.security.LockManager
import com.zex.tracker.security.NetworkForcer
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
    private val serviceController: ServiceController
) {
    private val scope = CoroutineScope(Dispatchers.IO)

    fun process(command: Command) {
        ZexLogger.i("CommandProcessor", "Processing command: \${command.type} (ID: \${command.id})")
        scope.launch {
            try {
                when (command.type) {
                    CommandType.LOCATE -> handleLocate()
                    CommandType.CONTINUOUS_TRACK -> handleStartTracking(command.parameters)
                    CommandType.STOP_TRACKING -> handleStopTracking()
                    CommandType.SCREAM -> handleScream()
                    CommandType.STOP_SCREAM -> handleStopScream()
                    CommandType.LOCK -> handleLock()
                    CommandType.ENABLE_NET -> networkForcer.forceNetwork()
                    CommandType.STOLEN_MODE -> handleStolenMode()
                    CommandType.FOUND_MODE -> handleFoundMode()
                    CommandType.STATUS -> handleStatus()
                    CommandType.PHOTO -> ZexLogger.w("CommandProcessor", "PHOTO ignored by rule")
                }
                // Respond to backend
                deviceRepo.sendCommandResponse(command.id, "EXECUTED")
            } catch (e: Exception) {
                ZexLogger.e("CommandProcessor", "Failed executing \${command.type}", e)
                deviceRepo.sendCommandResponse(command.id, "FAILED")
            }
        }
    }

    private suspend fun handleLocate() {
        val loc = locationTracker.getCurrentLocation()
        if (loc != null) {
            deviceRepo.sendLocation(loc)
        }
    }

    private fun handleStartTracking(params: Map<String, String>?) {
        val interval = params?.get("interval")?.toLongOrNull() ?: 30000L
        ServiceController.trackingInterval = interval
        ServiceController.isTracking = true
        serviceController.startProtection()
    }

    private fun handleStopTracking() {
        ServiceController.isTracking = false
        locationTracker.stopContinuous()
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
        // Wait for UI pin check naturally in real usage, but backend command stops immediately
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

    private fun handleStolenMode() {
        ServiceController.isStolen = true
        networkForcer.forceNetwork()
        handleStartTracking(mapOf("interval" to "30000"))
        // Optional scream
    }

    private fun handleFoundMode() {
        ServiceController.isStolen = false
        handleStopTracking()
        handleStopScream()
    }

    private suspend fun handleStatus() {
        deviceRepo.sendHeartbeat()
        handleLocate()
    }
}
""")

# ==========================================
# 6) Scream / Lock Managers and Activities
# ==========================================
write_file("security/ScreamManager.kt", """
package com.zex.tracker.security

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.RingtoneManager
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import com.zex.tracker.core.logging.ZexLogger
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ScreamManager @Inject constructor(@ApplicationContext private val context: Context) {
    private var mediaPlayer: MediaPlayer? = null
    private val vibrator: Vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        val vm = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as VibratorManager
        vm.defaultVibrator
    } else {
        context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
    }

    fun startScream() {
        try {
            val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            audioManager.setStreamVolume(AudioManager.STREAM_ALARM, audioManager.getStreamMaxVolume(AudioManager.STREAM_ALARM), 0)

            val uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
            mediaPlayer = MediaPlayer().apply {
                setDataSource(context, uri)
                setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ALARM).build())
                isLooping = true
                prepare()
                start()
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(VibrationEffect.createWaveform(longArrayOf(0, 1000, 1000), 0))
            } else {
                vibrator.vibrate(longArrayOf(0, 1000, 1000), 0)
            }
            ZexLogger.i("ScreamManager", "Scream started")
        } catch (e: Exception) {
            ZexLogger.e("ScreamManager", "Failed to start scream", e)
        }
    }

    fun stopScream() {
        try {
            mediaPlayer?.stop()
            mediaPlayer?.release()
            mediaPlayer = null
            vibrator.cancel()
            ZexLogger.i("ScreamManager", "Scream stopped")
        } catch (e: Exception) {
            ZexLogger.e("ScreamManager", "Failed to stop scream", e)
        }
    }
}
""")

write_file("security/LockManager.kt", """
package com.zex.tracker.security

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.receiver.ZexDeviceAdminReceiver
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LockManager @Inject constructor(@ApplicationContext private val context: Context) {
    private val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
    private val compName = ComponentName(context, ZexDeviceAdminReceiver::class.java)

    fun isDeviceAdminActive(): Boolean = dpm.isAdminActive(compName)

    fun lockNow() {
        try {
            if (isDeviceAdminActive()) {
                dpm.lockNow()
                ZexLogger.i("LockManager", "Device locked via admin")
            } else {
                ZexLogger.w("LockManager", "Cannot lock: Device admin not active")
            }
        } catch (e: Exception) {
            ZexLogger.e("LockManager", "Lock failed", e)
        }
    }
}
""")

write_file("ui/screens/scream/ScreamActivity.kt", """
package com.zex.tracker.ui.screens.scream

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.security.ScreamManager
import com.zex.tracker.service.ServiceController
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class ScreamActivity : ComponentActivity() {

    @Inject lateinit var screamManager: ScreamManager
    @Inject lateinit var prefs: SecurePrefs

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        screamManager.startScream()
        
        setContent {
            var pinInput by remember { mutableStateOf("") }
            var error by remember { mutableStateOf(false) }

            Column(
                modifier = Modifier.fillMaxSize().background(Color.Red).padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Text("DEVICE MARKED AS STOLEN", color = Color.White, style = MaterialTheme.typography.headlineLarge)
                Spacer(Modifier.height(32.dp))
                OutlinedTextField(
                    value = pinInput,
                    onValueChange = { pinInput = it },
                    label = { Text("Enter PIN to stop") },
                    colors = TextFieldDefaults.colors(focusedContainerColor = Color.White, unfocusedContainerColor = Color.White)
                )
                if (error) Text("Incorrect PIN", color = Color.Yellow)
                Spacer(Modifier.height(16.dp))
                Button(onClick = {
                    val savedPin = prefs.getString(ZexConstants.KEY_PIN_CODE)
                    if (pinInput == savedPin) {
                        screamManager.stopScream()
                        ServiceController.isScreaming = false
                        finish()
                    } else {
                        error = true
                    }
                }) {
                    Text("STOP")
                }
            }
        }
    }

    override fun onBackPressed() {
        // block back
    }
}
""")

write_file("ui/screens/lock/LockActivity.kt", """
package com.zex.tracker.ui.screens.lock

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.data.local.prefs.SecurePrefs
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class LockActivity : ComponentActivity() {

    @Inject lateinit var prefs: SecurePrefs

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            var pinInput by remember { mutableStateOf("") }
            
            Column(
                modifier = Modifier.fillMaxSize().background(Color.Black).padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Text("LOCKED BY OWNER", color = Color.White, style = MaterialTheme.typography.headlineLarge)
                Spacer(Modifier.height(32.dp))
                OutlinedTextField(
                    value = pinInput,
                    onValueChange = { pinInput = it },
                    label = { Text("Enter PIN to unlock") },
                    colors = TextFieldDefaults.colors(focusedContainerColor = Color.White, unfocusedContainerColor = Color.White)
                )
                Spacer(Modifier.height(16.dp))
                Button(onClick = {
                    val savedPin = prefs.getString(ZexConstants.KEY_PIN_CODE)
                    if (pinInput == savedPin) {
                        finish()
                    }
                }) {
                    Text("UNLOCK")
                }
            }
        }
    }
    
    override fun onBackPressed() {}
}
""")

# ==========================================
# 7) Foreground Service
# ==========================================
write_file("service/ServiceController.kt", """
package com.zex.tracker.service

import android.content.Context
import android.content.Intent
import android.os.Build
import com.zex.tracker.core.logging.ZexLogger
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ServiceController @Inject constructor(@ApplicationContext private val context: Context) {
    companion object {
        var isTracking: Boolean = false
        var trackingInterval: Long = 30000L
        var isScreaming: Boolean = false
        var isStolen: Boolean = false
    }

    fun startProtection() {
        try {
            val intent = Intent(context, ZexForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
            ZexLogger.i("ServiceController", "Requested Foreground Service start")
        } catch (e: Exception) {
            ZexLogger.e("ServiceController", "Failed to start service", e)
        }
    }

    fun stopProtection() {
        try {
            context.stopService(Intent(context, ZexForegroundService::class.java))
            ZexLogger.i("ServiceController", "Requested Foreground Service stop")
        } catch (e: Exception) {
            ZexLogger.e("ServiceController", "Failed to stop service", e)
        }
    }
}
""")

write_file("service/ZexForegroundService.kt", """
package com.zex.tracker.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.zex.tracker.R
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.remote.firebase.FirebaseCommandListener
import com.zex.tracker.security.location.LocationTracker
import com.zex.tracker.data.repository.DeviceRepository
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.*
import javax.inject.Inject

@AndroidEntryPoint
class ZexForegroundService : Service() {

    @Inject lateinit var locationTracker: LocationTracker
    @Inject lateinit var deviceRepo: DeviceRepository
    @Inject lateinit var firebaseListener: FirebaseCommandListener

    private val job = SupervisorJob()
    private val scope = CoroutineScope(Dispatchers.IO + job)
    
    override fun onCreate() {
        super.onCreate()
        ZexLogger.i("ZexForegroundService", "Service Created")
        startForeground(1001, createNotification())
        
        firebaseListener.startListening()
        startPeriodicHeartbeat()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        ZexLogger.i("ZexForegroundService", "onStartCommand")
        manageTracking()
        return START_STICKY
    }

    private fun manageTracking() {
        if (ServiceController.isTracking || ServiceController.isStolen) {
            locationTracker.startContinuous(ServiceController.trackingInterval) { loc ->
                scope.launch {
                    deviceRepo.sendLocation(loc)
                }
            }
        } else {
            locationTracker.stopContinuous()
        }
    }

    private fun startPeriodicHeartbeat() {
        scope.launch {
            while (isActive) {
                delay(if (ServiceController.isStolen) 30000L else 15 * 60 * 1000L)
                try {
                    deviceRepo.sendHeartbeat()
                } catch (e: Exception) {
                    ZexLogger.e("ZexForegroundService", "Periodic heartbeat failed", e)
                }
            }
        }
    }

    private fun createNotification(): android.app.Notification {
        val channelId = "zex_protection_channel"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val chan = NotificationChannel(channelId, "ZEX Protection", NotificationManager.IMPORTANCE_LOW)
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(chan)
        }
        return NotificationCompat.Builder(this, channelId)
            .setContentTitle("ZEX Protection")
            .setContentText("Protection is active")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        super.onDestroy()
        job.cancel()
        locationTracker.stopContinuous()
        firebaseListener.stopListening()
        ZexLogger.w("ZexForegroundService", "Service Destroyed")
        // Try to revive via intent broadcast or worker if killed by OS
        sendBroadcast(Intent("com.zex.tracker.REVIVE_SERVICE"))
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
""")

# ==========================================
# 8) Workers & 9) Firebase Listener
# ==========================================
write_file("data/remote/firebase/FirebaseCommandListener.kt", """
package com.zex.tracker.data.remote.firebase

import com.google.firebase.database.DataSnapshot
import com.google.firebase.database.DatabaseError
import com.google.firebase.database.FirebaseDatabase
import com.google.firebase.database.ValueEventListener
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.domain.model.Command
import com.zex.tracker.domain.model.CommandStatus
import com.zex.tracker.domain.model.CommandType
import com.zex.tracker.service.CommandProcessor
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class FirebaseCommandListener @Inject constructor(
    private val prefs: SecurePrefs,
    private val commandProcessor: CommandProcessor
) {
    private val db = FirebaseDatabase.getInstance()
    private var commandRef: com.google.firebase.database.DatabaseReference? = null
    private var listener: ValueEventListener? = null

    fun startListening() {
        val uid = prefs.getString(ZexConstants.KEY_DEVICE_UID)
        if (uid.isNullOrEmpty()) return

        ZexLogger.i("Firebase", "Starting Firebase RTDB listener for \$uid")
        commandRef = db.getReference("devices/\$uid/pending_commands")
        
        listener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                snapshot.children.forEach { child ->
                    try {
                        val idStr = child.key ?: return@forEach
                        val typeStr = child.child("type").getValue(String::class.java) ?: return@forEach
                        val type = CommandType.valueOf(typeStr)
                        
                        val params = mutableMapOf<String, String>()
                        child.child("parameters").children.forEach { p ->
                            params[p.key!!] = p.getValue(String::class.java) ?: ""
                        }

                        val cmd = Command(idStr.toInt(), type, params, CommandStatus.PENDING)
                        commandProcessor.process(cmd)
                        
                        // Remove from firebase after queuing
                        child.ref.removeValue()
                    } catch (e: Exception) {
                        ZexLogger.e("Firebase", "Failed parsing command", e)
                    }
                }
            }
            override fun onCancelled(error: DatabaseError) {
                ZexLogger.e("Firebase", "RTDB Cancelled: \${error.message}")
            }
        }
        commandRef?.addValueEventListener(listener!!)
    }

    fun stopListening() {
        listener?.let { commandRef?.removeEventListener(it) }
    }
}
""")

write_file("worker/HeartbeatWorker.kt", """
package com.zex.tracker.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.repository.DeviceRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

@HiltWorker
class HeartbeatWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val deviceRepo: DeviceRepository
) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        return try {
            ZexLogger.i("HeartbeatWorker", "Running scheduled heartbeat")
            deviceRepo.sendHeartbeat()
            Result.success()
        } catch (e: Exception) {
            ZexLogger.e("HeartbeatWorker", "Heartbeat failed", e)
            Result.retry()
        }
    }
}
""")

write_file("worker/ServiceReviverWorker.kt", """
package com.zex.tracker.worker

import android.content.Context
import androidx.work.Worker
import androidx.work.WorkerParameters
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.service.ServiceController

class ServiceReviverWorker(
    private val context: Context,
    params: WorkerParameters
) : Worker(context, params) {
    override fun doWork(): Result {
        ZexLogger.i("ServiceReviverWorker", "Checking if service is alive")
        val controller = ServiceController(context)
        controller.startProtection()
        return Result.success()
    }
}
""")

# ==========================================
# 10) FCM Service
# ==========================================
write_file("service/ZexFcmService.kt", """
package com.zex.tracker.service

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.domain.model.Command
import com.zex.tracker.domain.model.CommandStatus
import com.zex.tracker.domain.model.CommandType
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class ZexFcmService : FirebaseMessagingService() {

    @Inject lateinit var prefs: SecurePrefs
    @Inject lateinit var commandProcessor: CommandProcessor

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        ZexLogger.i("FCM", "New FCM token generated: \$token")
        // Note: Store local, sync with backend on next heartbeat if endpoint doesn't exist yet
        prefs.putString("fcm_token", token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        ZexLogger.i("FCM", "Received FCM Message")
        
        try {
            val data = message.data
            val cmdId = data["id"]?.toIntOrNull() ?: return
            val typeStr = data["type"] ?: return
            val type = CommandType.valueOf(typeStr)
            
            val cmd = Command(cmdId, type, data, CommandStatus.PENDING)
            commandProcessor.process(cmd)
        } catch (e: Exception) {
            ZexLogger.e("FCM", "Failed to process FCM data", e)
        }
    }
}
""")

# ==========================================
# 11) Receivers
# ==========================================
write_file("receiver/BootReceiver.kt", """
package com.zex.tracker.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.service.ServiceController

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED || 
            intent.action == Intent.ACTION_LOCKED_BOOT_COMPLETED || 
            intent.action == "android.intent.action.QUICKBOOT_POWERON") {
            ZexLogger.w("BootReceiver", "Device Booted. Starting Service.")
            ServiceController(context).startProtection()
        }
    }
}
""")

write_file("receiver/AlarmReceiver.kt", """
package com.zex.tracker.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.service.ServiceController

class AlarmReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        ZexLogger.i("AlarmReceiver", "Reviving service via Alarm")
        ServiceController(context).startProtection()
    }
}
""")

# ==========================================
# 12) Extended Repositories
# ==========================================
write_file("data/remote/dto/Payloads.kt", """
package com.zex.tracker.data.remote.dto

data class LocationPayload(
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float,
    val battery: Int,
    val network: String
)

data class HeartbeatPayload(
    val device_uid: String,
    val battery: Int
)

data class CommandResponsePayload(
    val status: String,
    val message: String? = null
)
""")

write_file("data/remote/api/ZexExtendedApi.kt", """
package com.zex.tracker.data.remote.api

import com.zex.tracker.data.remote.dto.*
import retrofit2.Response
import retrofit2.http.*

interface ZexExtendedApi : ZexApi {
    @POST("locations")
    suspend fun sendLocation(@Body payload: LocationPayload): Response<Unit>

    @POST("devices/heartbeat")
    suspend fun sendHeartbeat(@Body payload: HeartbeatPayload): Response<Unit>

    @POST("commands/{id}/response")
    suspend fun sendCommandResponse(@Path("id") id: Int, @Body payload: CommandResponsePayload): Response<Unit>

    @POST("alerts")
    suspend fun sendAlert(@Body payload: Map<String, String>): Response<Unit>
}
""")

# Notice: I am cheating slightly by extending ZexApi to avoid replacing it. In actual Dagger, we can just bind ZexExtendedApi or cast.
# But it's safer to just rewrite ZexApi entirely to contain all routes. Let's rewrite ZexApi.kt
write_file("data/remote/api/ZexApi.kt", """
package com.zex.tracker.data.remote.api

import com.zex.tracker.data.remote.dto.*
import retrofit2.Response
import retrofit2.http.*

interface ZexApi {
    @POST("auth/register")
    suspend fun registerOwner(@Body request: RegisterRequest): Response<AuthResponse>

    @POST("auth/login")
    suspend fun loginOwner(@Body request: LoginRequest): Response<AuthResponse>

    @GET("auth/me")
    suspend fun getOwnerMe(): Response<AuthResponse>

    @POST("devices/register")
    suspend fun registerDevice(@Body request: DeviceRegisterRequest): Response<DeviceRegisterResponse>

    @POST("locations")
    suspend fun sendLocation(@Body payload: LocationPayload): Response<Unit>

    @POST("devices/heartbeat")
    suspend fun sendHeartbeat(@Body payload: HeartbeatPayload): Response<Unit>

    @POST("commands/{id}/response")
    suspend fun sendCommandResponse(@Path("id") id: Int, @Body payload: CommandResponsePayload): Response<Unit>

    @POST("alerts")
    suspend fun sendAlert(@Body payload: Map<String, String>): Response<Unit>
}
""")

write_file("data/repository/DeviceRepository.kt", """
package com.zex.tracker.data.repository

import android.content.Context
import android.location.Location
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.core.utils.BatteryUtils
import com.zex.tracker.core.utils.NetworkUtils
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.data.remote.ApiResult
import com.zex.tracker.data.remote.api.ZexApi
import com.zex.tracker.data.remote.dto.*
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject

class DeviceRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val api: ZexApi,
    private val prefs: SecurePrefs
) : BaseRepository() {

    suspend fun registerDevice(request: DeviceRegisterRequest): ApiResult<DeviceRegisterResponse> = safeApiCall {
        api.registerDevice(request)
    }

    suspend fun sendLocation(location: Location): ApiResult<Unit> = safeApiCall {
        val payload = LocationPayload(
            latitude = location.latitude,
            longitude = location.longitude,
            accuracy = location.accuracy,
            battery = BatteryUtils.getBatteryLevel(context),
            network = NetworkUtils.getNetworkType(context)
        )
        api.sendLocation(payload)
    }

    suspend fun sendHeartbeat(): ApiResult<Unit> = safeApiCall {
        val payload = HeartbeatPayload(
            device_uid = prefs.getString(ZexConstants.KEY_DEVICE_UID) ?: "",
            battery = BatteryUtils.getBatteryLevel(context)
        )
        api.sendHeartbeat(payload)
    }

    suspend fun sendCommandResponse(cmdId: Int, status: String): ApiResult<Unit> = safeApiCall {
        api.sendCommandResponse(cmdId, CommandResponsePayload(status))
    }
}
""")

# ==========================================
# 13) Dashboard Screen update
# ==========================================
write_file("ui/screens/dashboard/DashboardScreen.kt", """
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

@Composable
fun DashboardScreen(prefs: SecurePrefs) {
    val uid = prefs.getString(ZexConstants.KEY_DEVICE_UID) ?: "Unknown UID"
    val context = LocalContext.current
    var serviceRunning by remember { mutableStateOf(false) } // Basic mock

    Column(modifier = Modifier.fillMaxSize().padding(24.dp)) {
        Text("ZEX Dashboard", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(16.dp))
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Device UID: \$uid")
                Text("Tracking: \${ServiceController.isTracking}")
                Text("Stolen Mode: \${ServiceController.isStolen}")
            }
        }
        Spacer(Modifier.height(24.dp))
        PrimaryButton(
            text = "Start Protection Service",
            onClick = {
                ServiceController(context).startProtection()
                serviceRunning = true
            }
        )
        Spacer(Modifier.height(8.dp))
        PrimaryButton(
            text = "Stop Protection Service",
            onClick = {
                ServiceController(context).stopProtection()
                serviceRunning = false
            }
        )
    }
}
""")
