import os

base_dir = r"C:\Users\moham\OneDrive\Desktop\z\mobile\zex-app\app\src\main"
pkg = os.path.join(base_dir, "java", "com", "zex", "tracker")

def write_file(path, content):
    full_path = os.path.join(pkg, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        content = content.replace(r"\${", "${").replace(r"\$", "$")
        f.write(content.strip() + "\n")

# B1 & B2 & B5: Payloads
write_file("data/remote/dto/Payloads.kt", r"""
package com.zex.tracker.data.remote.dto

data class LocationPayload(
    val device_uid: String,
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float,
    val altitude: Double,
    val speed: Float,
    val bearing: Float,
    val provider: String,
    val battery_level: Int,
    val network_type: String,
    val address: String?,
    val recorded_at: String
)

data class HeartbeatPayload(
    val device_uid: String,
    val battery_level: Int
)

data class CommandResponsePayload(
    val device_uid: String,
    val status: String,
    val response: Map<String, String>? = null
)

data class HeartbeatResponsePayload(
    val pending_commands: List<CommandDto>? = null,
    val owner_is_searching: Boolean = false,
    val search_interval_seconds: Int = 30,
    val owner_password_hash: String? = null
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

write_file("data/remote/dto/DeviceDto.kt", r"""
package com.zex.tracker.data.remote.dto

data class DeviceRegisterRequest(
    val device_uid: String,
    val device_name: String,
    val device_model: String,
    val android_version: String,
    val sim_iccid: String?
)

data class DeviceRegisterResponse(
    val device: DeviceDto,
    val device_token: String
)

data class DeviceDto(
    val id: Long,
    val device_uid: String,
    val device_name: String,
    val device_model: String,
    val android_version: String
)
""")

# B3 & B4: ZexApi.kt
write_file("data/remote/api/ZexApi.kt", r"""
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
    suspend fun sendHeartbeat(@Body payload: HeartbeatPayload): Response<HeartbeatResponsePayload>

    @POST("commands/{command}/response")
    suspend fun sendCommandResponse(@Path("command") commandId: Int, @Body payload: CommandResponsePayload): Response<Unit>

    @POST("alerts")
    suspend fun sendAlert(@Body payload: Map<String, String>): Response<Unit>

    @GET("devices/{device}/status")
    suspend fun getDeviceStatus(@Path("device") deviceId: Long): Response<DeviceStatusPayload>
}
""")

# DeviceRepository
write_file("data/repository/DeviceRepository.kt", r"""
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
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
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
        val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        val recordedAt = dateFormat.format(Date(location.time))
        val payload = LocationPayload(
            device_uid = prefs.getString(ZexConstants.KEY_DEVICE_UID) ?: "",
            latitude = location.latitude,
            longitude = location.longitude,
            accuracy = location.accuracy,
            altitude = location.altitude,
            speed = location.speed,
            bearing = location.bearing,
            provider = location.provider ?: "gps",
            battery_level = BatteryUtils.getBatteryLevel(context),
            network_type = NetworkUtils.getNetworkType(context),
            address = null,
            recorded_at = recordedAt
        )
        api.sendLocation(payload)
    }

    suspend fun sendHeartbeat(): ApiResult<HeartbeatResponsePayload> = safeApiCall {
        val payload = HeartbeatPayload(
            device_uid = prefs.getString(ZexConstants.KEY_DEVICE_UID) ?: "",
            battery_level = BatteryUtils.getBatteryLevel(context)
        )
        api.sendHeartbeat(payload)
    }

    suspend fun sendCommandResponse(cmdId: Int, status: String, responseData: Map<String, String>? = null): ApiResult<Unit> = safeApiCall {
        val payload = CommandResponsePayload(
            device_uid = prefs.getString(ZexConstants.KEY_DEVICE_UID) ?: "",
            status = status,
            response = responseData
        )
        api.sendCommandResponse(cmdId, payload)
    }

    suspend fun getDeviceStatus(): ApiResult<DeviceStatusPayload> = safeApiCall {
        val deviceId = prefs.getLong("device_numeric_id", 0L)
        api.getDeviceStatus(deviceId)
    }

    suspend fun sendAlert(payload: Map<String, String>): ApiResult<Unit> = safeApiCall {
        api.sendAlert(payload)
    }
}
""")

# B8: LocationTracker
write_file("security/location/LocationTracker.kt", r"""
package com.zex.tracker.security.location

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.os.Looper
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
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

    suspend fun getCurrentLocation(): Location? {
        if (!hasLocationPermission()) {
            ZexLogger.w("LocationTracker", "Location permission denied. Failing gracefully.")
            return null
        }
        return try {
            fusedLocationClient.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, null).await()
        } catch (e: SecurityException) {
            ZexLogger.e("LocationTracker", "SecurityException getting location", e)
            null
        } catch (e: Exception) {
            ZexLogger.e("LocationTracker", "Failed to get location", e)
            null
        }
    }

    fun startContinuous(intervalMs: Long, onLocation: (Location) -> Unit) {
        if (!hasLocationPermission()) {
            ZexLogger.w("LocationTracker", "Location permission denied. Cannot start continuous.")
            return
        }
        try {
            // Remove existing to prevent leak/race
            locationCallback?.let { fusedLocationClient.removeLocationUpdates(it) }
            
            val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, intervalMs)
                .setMinUpdateIntervalMillis(intervalMs / 2)
                .build()

            locationCallback = object : LocationCallback() {
                override fun onLocationResult(result: LocationResult) {
                    result.lastLocation?.let(onLocation)
                }
            }

            fusedLocationClient.requestLocationUpdates(request, locationCallback!!, Looper.getMainLooper())
            ZexLogger.i("LocationTracker", "Started continuous tracking at ${intervalMs}ms")
        } catch (e: SecurityException) {
            ZexLogger.e("LocationTracker", "SecurityException in startContinuous", e)
        }
    }

    fun stopContinuous() {
        try {
            locationCallback?.let { fusedLocationClient.removeLocationUpdates(it) }
            locationCallback = null
            ZexLogger.i("LocationTracker", "Stopped continuous tracking")
        } catch (e: Exception) {
            ZexLogger.e("LocationTracker", "Error stopping continuous", e)
        }
    }
    
    private fun hasLocationPermission(): Boolean {
        return ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
               ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
    }
}
""")

# B9: HourlyAlarmReceiver
write_file("receiver/HourlyAlarmReceiver.kt", r"""
package com.zex.tracker.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.security.Scheduler
import com.zex.tracker.security.SearchModeManager
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class HourlyAlarmReceiver : BroadcastReceiver() {

    @Inject lateinit var searchModeManager: SearchModeManager
    @Inject lateinit var scheduler: Scheduler

    override fun onReceive(context: Context, intent: Intent) {
        ZexLogger.i("HourlyAlarmReceiver", "Waking up to perform search mode check")
        val pendingResult = goAsync()
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                searchModeManager.checkOwnerSearching()
            } catch (e: Exception) {
                ZexLogger.e("HourlyAlarmReceiver", "Failed search check", e)
            } finally {
                scheduler.scheduleHourlyChecks() // reschedule next alarm
                pendingResult.finish()
            }
        }
    }
}
""")

# B7 & B6: ScreamActivity & CommandProcessor
write_file("service/CommandProcessor.kt", r"""
package com.zex.tracker.service

import android.content.Context
import android.content.Intent
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.data.repository.DeviceRepository
import com.zex.tracker.domain.model.CommandType
import com.zex.tracker.data.remote.dto.CommandDto
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

    fun process(command: CommandDto) {
        ZexLogger.i("CommandProcessor", "Processing command: ${command.type}")
        scope.launch {
            try {
                when (command.type) {
                    "LOCATE" -> handleLocate()
                    "CONTINUOUS_TRACK" -> {
                        val interval = command.parameters?.get("interval")?.toIntOrNull() ?: 30
                        searchModeManager.enterSearchMode("command_track", interval)
                    }
                    "STOP_TRACKING" -> searchModeManager.exitSearchMode("command_stop")
                    "SCREAM" -> handleScream()
                    "STOP_SCREAM" -> handleStopScream()
                    "LOCK" -> handleLock()
                    "ENABLE_NET" -> networkForcer.forceNetwork()
                    "STOLEN_MODE" -> {
                        prefs.putBoolean("isStolen", true)
                        ServiceController.isStolen = true
                        searchModeManager.enterSearchMode("stolen_mode", 30)
                    }
                    "FOUND_MODE" -> {
                        prefs.putBoolean("isStolen", false)
                        ServiceController.isStolen = false
                        searchModeManager.exitSearchMode("found_mode")
                        handleStopScream()
                        context.sendBroadcast(Intent("ACTION_STOP_SCREAM_AND_FINISH"))
                    }
                    "STATUS" -> handleStatus()
                    "PHOTO" -> ZexLogger.w("CommandProcessor", "PHOTO ignored by rule")
                }
                deviceRepo.sendCommandResponse(command.id, "EXECUTED")
            } catch (e: Exception) {
                ZexLogger.e("CommandProcessor", "Failed executing ${command.type}", e)
                deviceRepo.sendCommandResponse(command.id, "FAILED", mapOf("error" to (e.message ?: "Unknown")))
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

write_file("ui/screens/scream/ScreamActivity.kt", r"""
package com.zex.tracker.ui.screens.scream

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
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
import at.favre.lib.crypto.bcrypt.BCrypt
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.security.ScreamManager
import com.zex.tracker.service.ServiceController
import com.zex.tracker.core.logging.ZexLogger
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class ScreamActivity : ComponentActivity() {

    @Inject lateinit var screamManager: ScreamManager
    @Inject lateinit var prefs: SecurePrefs

    private val stopReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == "ACTION_STOP_SCREAM_AND_FINISH") {
                screamManager.stopScream()
                ServiceController.isScreaming = false
                finish()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        screamManager.startScream()
        
        val filter = IntentFilter("ACTION_STOP_SCREAM_AND_FINISH")
        androidx.core.content.ContextCompat.registerReceiver(this, stopReceiver, filter, androidx.core.content.ContextCompat.RECEIVER_NOT_EXPORTED)

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
                    label = { Text("Enter Password/PIN to stop") },
                    colors = TextFieldDefaults.colors(focusedContainerColor = Color.White, unfocusedContainerColor = Color.White)
                )
                if (error) Text("Incorrect Password", color = Color.Yellow)
                Spacer(Modifier.height(16.dp))
                Button(onClick = {
                    CoroutineScope(Dispatchers.IO).launch {
                        val storedHash = prefs.getString("owner_password_hash")
                        if (!storedHash.isNullOrEmpty()) {
                            val verified = BCrypt.verifyer().verify(pinInput.toCharArray(), storedHash.toByteArray()).verified
                            if (verified) {
                                screamManager.stopScream()
                                ServiceController.isScreaming = false
                                finish()
                            } else {
                                error = true
                            }
                        } else {
                            // API fallback not fully needed if we have hash, but we gracefully log
                            ZexLogger.w("ScreamActivity", "No stored hash available to verify.")
                            error = true
                        }
                    }
                }) {
                    Text("STOP")
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        try { unregisterReceiver(stopReceiver) } catch (e: Exception) {}
    }

    override fun onBackPressed() {
        // block back
    }
}
""")

# SearchModeManager (Store owner_password_hash)
write_file("security/SearchModeManager.kt", r"""
package com.zex.tracker.security

import android.content.Context
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.data.repository.DeviceRepository
import com.zex.tracker.service.ServiceController
import com.zex.tracker.data.remote.ApiResult
import com.zex.tracker.data.remote.dto.HeartbeatResponsePayload
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SearchModeManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val deviceRepo: DeviceRepository,
    private val prefs: SecurePrefs,
    private val networkForcer: NetworkForcer
) {
    fun enterSearchMode(reason: String, intervalSeconds: Int) {
        ZexLogger.i("SearchModeManager", "Entering search mode: $reason")
        ServiceController.isSearching = true
        ServiceController.trackingInterval = (intervalSeconds * 1000).toLong()
        ServiceController(context).restartProtection()
    }

    fun exitSearchMode(reason: String) {
        ZexLogger.i("SearchModeManager", "Exiting search mode: $reason")
        ServiceController.isSearching = false
        ServiceController.trackingInterval = 15 * 60 * 1000L
        ServiceController(context).restartProtection()
    }

    suspend fun checkOwnerSearching(): HeartbeatResponsePayload? {
        networkForcer.forceNetwork()
        val result = deviceRepo.sendHeartbeat()
        if (result is ApiResult.Success) {
            val payload = result.data
            prefs.putLong("lastSearchCheckAt", System.currentTimeMillis())
            
            // Save hash
            payload.owner_password_hash?.let { hash ->
                prefs.putString("owner_password_hash", hash)
            }
            
            if (payload.owner_is_searching) {
                if (!ServiceController.isSearching) {
                    enterSearchMode("owner_is_searching", payload.search_interval_seconds)
                } else if (ServiceController.trackingInterval != (payload.search_interval_seconds * 1000).toLong()) {
                    enterSearchMode("interval_updated", payload.search_interval_seconds)
                }
            } else {
                if (ServiceController.isSearching && !ServiceController.isStolen) {
                    exitSearchMode("owner_stopped_searching")
                }
            }
            return payload
        }
        return null
    }
}
""")

# B11: NetworkModule
write_file("di/NetworkModule.kt", r"""
package com.zex.tracker.di

import com.zex.tracker.BuildConfig
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.data.remote.api.ZexApi
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
            // Redact passwords from request body logs
            if (message.contains("password") || message.contains("pin_code") || message.contains("password_hash")) {
                ZexLogger.d("OkHttp", "[REDACTED SENSITIVE BODY]")
            } else {
                ZexLogger.d("OkHttp", message)
            }
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
    fun provideZexApi(retrofit: Retrofit): ZexApi {
        return retrofit.create(ZexApi::class.java)
    }
}
""")
