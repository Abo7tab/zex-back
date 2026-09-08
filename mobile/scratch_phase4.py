import os

base_dir = r"C:\Users\moham\OneDrive\Desktop\z\mobile\zex-app\app\src\main"
pkg = os.path.join(base_dir, "java", "com", "zex", "tracker")

def write_file(path, content):
    full_path = os.path.join(pkg, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        # Prevent python string template issues
        content = content.replace(r"\${", "${").replace(r"\$", "$")
        f.write(content.strip() + "\n")

# ==========================================
# 1) Prefs & Constants
# ==========================================
write_file("data/local/prefs/SecurePrefs.kt", r"""
package com.zex.tracker.data.local.prefs

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.core.logging.ZexLogger
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SecurePrefs @Inject constructor(@ApplicationContext context: Context) {

    private val prefs: SharedPreferences = try {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        EncryptedSharedPreferences.create(
            context,
            ZexConstants.PREFS_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    } catch (e: Exception) {
        ZexLogger.e("SecurePrefs", "Failed to init EncryptedSharedPreferences. Falling back.", e)
        context.getSharedPreferences(ZexConstants.FALLBACK_PREFS_NAME, Context.MODE_PRIVATE)
    }

    fun putString(key: String, value: String?) = prefs.edit().putString(key, value).apply()
    fun getString(key: String, default: String? = null): String? = prefs.getString(key, default)

    fun putBoolean(key: String, value: Boolean) = prefs.edit().putBoolean(key, value).apply()
    fun getBoolean(key: String, default: Boolean = false): Boolean = prefs.getBoolean(key, default)

    fun putInt(key: String, value: Int) = prefs.edit().putInt(key, value).apply()
    fun getInt(key: String, default: Int = 0): Int = prefs.getInt(key, default)

    fun putLong(key: String, value: Long) = prefs.edit().putLong(key, value).apply()
    fun getLong(key: String, default: Long = 0L): Long = prefs.getLong(key, default)

    fun clear() = prefs.edit().clear().apply()
}
""")

# ==========================================
# 2) DTOs & API
# ==========================================
write_file("data/remote/dto/Payloads.kt", r"""
package com.zex.tracker.data.remote.dto

import com.zex.tracker.domain.model.Command

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

data class HeartbeatResponsePayload(
    val pending_commands: List<CommandDto>? = null,
    val owner_is_searching: Boolean = false,
    val search_interval_seconds: Int = 30
)

data class DeviceStatusPayload(
    val device_uid: String,
    val is_searching: Boolean,
    val is_stolen: Boolean,
    val is_screaming: Boolean,
    val is_tracking_continuous: Boolean,
    val search_interval_seconds: Int,
    val battery_level: Int
)

data class CommandDto(
    val id: Int,
    val type: String,
    val parameters: Map<String, String>? = null,
    val status: String
)
""")

write_file("data/remote/api/ZexExtendedApi.kt", r"""
package com.zex.tracker.data.remote.api

import com.zex.tracker.data.remote.dto.*
import retrofit2.Response
import retrofit2.http.*

interface ZexExtendedApi : ZexApi {
    @POST("locations")
    suspend fun sendLocation(@Body payload: LocationPayload): Response<Unit>

    @POST("devices/heartbeat")
    suspend fun sendHeartbeat(@Body payload: HeartbeatPayload): Response<HeartbeatResponsePayload>

    @POST("commands/{id}/response")
    suspend fun sendCommandResponse(@Path("id") id: Int, @Body payload: CommandResponsePayload): Response<Unit>

    @POST("alerts")
    suspend fun sendAlert(@Body payload: Map<String, String>): Response<Unit>

    @GET("devices/{deviceUid}/status")
    suspend fun getDeviceStatus(@Path("deviceUid") deviceUid: String): Response<DeviceStatusPayload>
}
""")

write_file("data/repository/DeviceRepository.kt", r"""
package com.zex.tracker.data.repository

import android.content.Context
import android.location.Location
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.core.utils.BatteryUtils
import com.zex.tracker.core.utils.NetworkUtils
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.data.remote.ApiResult
import com.zex.tracker.data.remote.api.ZexExtendedApi
import com.zex.tracker.data.remote.dto.*
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject

class DeviceRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val api: ZexExtendedApi,
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

    suspend fun sendHeartbeat(): ApiResult<HeartbeatResponsePayload> = safeApiCall {
        val payload = HeartbeatPayload(
            device_uid = prefs.getString(ZexConstants.KEY_DEVICE_UID) ?: "",
            battery = BatteryUtils.getBatteryLevel(context)
        )
        api.sendHeartbeat(payload)
    }

    suspend fun sendCommandResponse(cmdId: Int, status: String): ApiResult<Unit> = safeApiCall {
        api.sendCommandResponse(cmdId, CommandResponsePayload(status))
    }

    suspend fun getDeviceStatus(): ApiResult<DeviceStatusPayload> = safeApiCall {
        val uid = prefs.getString(ZexConstants.KEY_DEVICE_UID) ?: ""
        api.getDeviceStatus(uid)
    }

    suspend fun sendAlert(payload: Map<String, String>): ApiResult<Unit> = safeApiCall {
        api.sendAlert(payload)
    }
}
""")

# ==========================================
# 3) SearchModeManager
# ==========================================
write_file("security/SearchModeManager.kt", r"""
package com.zex.tracker.security

import android.content.Context
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.data.remote.ApiResult
import com.zex.tracker.data.repository.DeviceRepository
import com.zex.tracker.service.ServiceController
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SearchModeManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val prefs: SecurePrefs,
    private val deviceRepo: DeviceRepository,
    private val networkForcer: NetworkForcer,
    private val serviceController: ServiceController
) {
    suspend fun checkOwnerSearching(): Boolean {
        prefs.putLong("lastSearchCheckAt", System.currentTimeMillis())
        val result = deviceRepo.sendHeartbeat()
        if (result is ApiResult.Success) {
            val payload = result.data
            syncSearchState(payload.owner_is_searching, payload.search_interval_seconds)
            return payload.owner_is_searching
        } else {
            // Fallback status check
            val statusResult = deviceRepo.getDeviceStatus()
            if (statusResult is ApiResult.Success) {
                val status = statusResult.data
                syncSearchState(status.is_searching, status.search_interval_seconds)
                return status.is_searching
            }
        }
        return prefs.getBoolean("isSearching", false)
    }

    private fun syncSearchState(isSearching: Boolean, interval: Int) {
        prefs.putBoolean("isSearching", isSearching)
        prefs.putInt("searchIntervalSeconds", interval)
        if (isSearching) {
            enterSearchMode("heartbeat_sync", interval)
        } else {
            // only exit if not stolen
            if (!prefs.getBoolean("isStolen", false)) {
                exitSearchMode("heartbeat_sync")
            }
        }
    }

    fun enterSearchMode(reason: String, intervalSeconds: Int = 30) {
        ZexLogger.i("SearchMode", "Entering search mode. Reason: \${reason}")
        prefs.putBoolean("isSearching", true)
        prefs.putInt("searchIntervalSeconds", intervalSeconds)
        networkForcer.forceNetwork()

        ServiceController.isTracking = true
        ServiceController.trackingInterval = intervalSeconds * 1000L
        ServiceController.isSearching = true
        serviceController.startProtection() // Refresh service
    }

    fun exitSearchMode(reason: String) {
        ZexLogger.i("SearchMode", "Exiting search mode. Reason: \${reason}")
        prefs.putBoolean("isSearching", false)
        ServiceController.isSearching = false
        
        if (!prefs.getBoolean("isStolen", false)) {
            ServiceController.isTracking = false
        }
        serviceController.startProtection() // Refresh service notification
    }
}
""")

# ==========================================
# 4) Scheduler & Hourly Check
# ==========================================
write_file("security/Scheduler.kt", r"""
package com.zex.tracker.security

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.ExistingPeriodicWorkPolicy
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.receiver.HourlyAlarmReceiver
import com.zex.tracker.worker.HourlyCheckWorker
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class Scheduler @Inject constructor(private val context: Context) {

    fun scheduleHourlyChecks() {
        scheduleAlarmManager()
        scheduleWorkManager()
    }

    private fun scheduleAlarmManager() {
        try {
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            val intent = Intent(context, HourlyAlarmReceiver::class.java)
            val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            }
            val pendingIntent = PendingIntent.getBroadcast(context, 1001, intent, flags)

            val triggerTime = System.currentTimeMillis() + AlarmManager.INTERVAL_HOUR

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && !alarmManager.canScheduleExactAlarms()) {
                ZexLogger.w("Scheduler", "Cannot schedule exact alarms, using inexact.")
                alarmManager.setInexactRepeating(AlarmManager.RTC_WAKEUP, triggerTime, AlarmManager.INTERVAL_HOUR, pendingIntent)
            } else {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent)
                } else {
                    alarmManager.setExact(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent)
                }
                ZexLogger.i("Scheduler", "Scheduled exact hourly alarm.")
            }
        } catch (e: Exception) {
            ZexLogger.e("Scheduler", "Failed scheduling alarm", e)
        }
    }

    private fun scheduleWorkManager() {
        val workRequest = PeriodicWorkRequestBuilder<HourlyCheckWorker>(1, TimeUnit.HOURS).build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            "HourlyCheckWorker",
            ExistingPeriodicWorkPolicy.KEEP,
            workRequest
        )
        ZexLogger.i("Scheduler", "Scheduled WorkManager hourly check.")
    }
}
""")

write_file("worker/HourlyCheckWorker.kt", r"""
package com.zex.tracker.worker

import android.content.Context
import android.content.Intent
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.security.NetworkForcer
import com.zex.tracker.security.SearchModeManager
import com.zex.tracker.security.location.LocationTracker
import com.zex.tracker.data.repository.DeviceRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

@HiltWorker
class HourlyCheckWorker @AssistedInject constructor(
    @Assisted private val context: Context,
    @Assisted params: WorkerParameters,
    private val searchModeManager: SearchModeManager,
    private val networkForcer: NetworkForcer,
    private val locationTracker: LocationTracker,
    private val deviceRepo: DeviceRepository
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        ZexLogger.i("HourlyCheckWorker", "Running hourly check")
        networkForcer.forceNetwork()
        val isSearching = searchModeManager.checkOwnerSearching()

        if (!isSearching) {
            ZexLogger.i("HourlyCheckWorker", "Not searching. Taking snapshot.")
            val loc = locationTracker.getCurrentLocation()
            if (loc != null) deviceRepo.sendLocation(loc)
        }
        
        // Re-schedule exact alarm
        context.sendBroadcast(Intent("com.zex.tracker.RESCHEDULE_ALARM"))
        return Result.success()
    }
}
""")

write_file("receiver/HourlyAlarmReceiver.kt", r"""
package com.zex.tracker.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.security.NetworkForcer
import com.zex.tracker.security.SearchModeManager
import com.zex.tracker.security.Scheduler
import com.zex.tracker.security.location.LocationTracker
import com.zex.tracker.data.repository.DeviceRepository
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class HourlyAlarmReceiver : BroadcastReceiver() {

    @Inject lateinit var searchModeManager: SearchModeManager
    @Inject lateinit var networkForcer: NetworkForcer
    @Inject lateinit var locationTracker: LocationTracker
    @Inject lateinit var deviceRepo: DeviceRepository
    @Inject lateinit var scheduler: Scheduler

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == "com.zex.tracker.RESCHEDULE_ALARM") {
            scheduler.scheduleHourlyChecks()
            return
        }

        ZexLogger.i("HourlyAlarmReceiver", "Woke up via AlarmManager")
        CoroutineScope(Dispatchers.IO).launch {
            try {
                networkForcer.forceNetwork()
                val isSearching = searchModeManager.checkOwnerSearching()
                if (!isSearching) {
                    val loc = locationTracker.getCurrentLocation()
                    if (loc != null) deviceRepo.sendLocation(loc)
                }
            } catch (e: Exception) {
                ZexLogger.e("HourlyAlarmReceiver", "Hourly check failed", e)
            } finally {
                scheduler.scheduleHourlyChecks()
            }
        }
    }
}
""")

# ==========================================
# 5) Refactoring ZexForegroundService & CommandProcessor
# ==========================================
write_file("service/ServiceController.kt", r"""
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
        var isSearching: Boolean = false
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

write_file("service/ZexForegroundService.kt", r"""
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
import com.zex.tracker.security.Scheduler
import com.zex.tracker.security.SearchModeManager
import com.zex.tracker.data.repository.DeviceRepository
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.*
import javax.inject.Inject

@AndroidEntryPoint
class ZexForegroundService : Service() {

    @Inject lateinit var locationTracker: LocationTracker
    @Inject lateinit var deviceRepo: DeviceRepository
    @Inject lateinit var firebaseListener: FirebaseCommandListener
    @Inject lateinit var scheduler: Scheduler
    @Inject lateinit var searchModeManager: SearchModeManager

    private val job = SupervisorJob()
    private val scope = CoroutineScope(Dispatchers.IO + job)
    
    override fun onCreate() {
        super.onCreate()
        ZexLogger.i("ZexForegroundService", "Service Created")
        startForeground(1001, createNotification())
        
        firebaseListener.startListening()
        scheduler.scheduleHourlyChecks()
        
        // Initial boot/start check
        scope.launch { searchModeManager.checkOwnerSearching() }
        startPeriodicHeartbeat()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        ZexLogger.i("ZexForegroundService", "onStartCommand")
        
        // Update notification
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(1001, createNotification())

        manageTracking()
        return START_STICKY
    }

    private fun manageTracking() {
        if (ServiceController.isTracking || ServiceController.isSearching || ServiceController.isStolen) {
            val interval = ServiceController.trackingInterval.coerceAtLeast(10000L)
            locationTracker.startContinuous(interval) { loc ->
                scope.launch { deviceRepo.sendLocation(loc) }
            }
        } else {
            locationTracker.stopContinuous()
        }
    }

    private fun startPeriodicHeartbeat() {
        scope.launch {
            while (isActive) {
                val delayMs = if (ServiceController.isSearching || ServiceController.isStolen) 30000L else 15 * 60 * 1000L
                delay(delayMs)
                try {
                    searchModeManager.checkOwnerSearching()
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
        
        val text = when {
            ServiceController.isStolen -> "Stolen mode active"
            ServiceController.isSearching -> "Search mode active"
            else -> "Protection active"
        }

        return NotificationCompat.Builder(this, channelId)
            .setContentTitle("ZEX")
            .setContentText(text)
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
        sendBroadcast(Intent("com.zex.tracker.REVIVE_SERVICE"))
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
""")

# ==========================================
# 6) SMS Commands
# ==========================================
write_file("receiver/SmsCommandReceiver.kt", r"""
package com.zex.tracker.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.domain.model.Command
import com.zex.tracker.domain.model.CommandStatus
import com.zex.tracker.domain.model.CommandType
import com.zex.tracker.service.CommandProcessor
import com.zex.tracker.security.SearchModeManager
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

@AndroidEntryPoint
class SmsCommandReceiver : BroadcastReceiver() {

    @Inject lateinit var prefs: SecurePrefs
    @Inject lateinit var commandProcessor: CommandProcessor
    @Inject lateinit var searchModeManager: SearchModeManager

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Telephony.Sms.Intents.SMS_RECEIVED_ACTION) {
            val msgs = Telephony.Sms.Intents.getMessagesFromIntent(intent)
            val ownerPhone = prefs.getString(ZexConstants.KEY_OWNER_PHONE) ?: return

            for (msg in msgs) {
                val sender = msg.originatingAddress ?: continue
                val body = msg.messageBody ?: continue

                val ownerLast8 = if (ownerPhone.length >= 8) ownerPhone.takeLast(8) else ownerPhone
                if (sender.endsWith(ownerLast8)) {
                    ZexLogger.i("SmsCommandReceiver", "Received SMS from owner: \${body}")
                    
                    if (body.startsWith("#ZEX#")) {
                        try { abortBroadcast() } catch (e: Exception) { }

                        val cmdStr = body.removePrefix("#ZEX#").trim()
                        when (cmdStr) {
                            "SEARCH_ON" -> searchModeManager.enterSearchMode("sms")
                            "SEARCH_OFF" -> searchModeManager.exitSearchMode("sms")
                            else -> {
                                try {
                                    val type = CommandType.valueOf(cmdStr)
                                    val cmd = Command((System.currentTimeMillis() % 100000).toInt(), type, null, CommandStatus.PENDING)
                                    commandProcessor.process(cmd)
                                } catch (e: Exception) {
                                    ZexLogger.w("SmsCommandReceiver", "Invalid SMS command type: \${cmdStr}")
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
""")

# ==========================================
# 7) Dashboard UI Update
# ==========================================
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
                FilterChip(selected = true, onClick = {}, label = { Text("Stolen") }, colors = FilterChipDefaults.filterChipColors(selectedContainerColor = MaterialTheme.colorScheme.error))
            }
            if (ServiceController.isSearching) {
                FilterChip(selected = true, onClick = {}, label = { Text("Searching") }, colors = FilterChipDefaults.filterChipColors(selectedContainerColor = MaterialTheme.colorScheme.primary))
            }
            if (!ServiceController.isStolen && !ServiceController.isSearching) {
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
