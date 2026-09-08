import os

base_dir = r"C:\Users\moham\OneDrive\Desktop\z\mobile\zex-app\app\src\main"
pkg = os.path.join(base_dir, "java", "com", "zex", "tracker")

def write_file(path, content):
    full_path = os.path.join(pkg, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

def write_res(path, content):
    full_path = os.path.join(base_dir, "res", path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

# 1) Constants
write_file("core/constants/ZexConstants.kt", """
package com.zex.tracker.core.constants

object ZexConstants {
    const val PREFS_NAME = "zex_secure_prefs"
    const val FALLBACK_PREFS_NAME = "zex_fallback_prefs"
    
    // Pref Keys
    const val KEY_OWNER_TOKEN = "owner_token"
    const val KEY_DEVICE_TOKEN = "device_token"
    const val KEY_DEVICE_UID = "device_uid"
    const val KEY_OWNER_ID = "owner_id"
    const val KEY_OWNER_NAME = "owner_name"
    const val KEY_OWNER_EMAIL = "owner_email"
    const val KEY_OWNER_PHONE = "owner_phone"
    const val KEY_PIN_CODE = "pin_code"
    const val KEY_IS_SETUP_COMPLETE = "is_setup_complete"
    const val KEY_LANGUAGE = "language"
    
    // Headers
    const val HEADER_AUTHORIZATION = "Authorization"
    const val HEADER_DEVICE_TOKEN = "X-Device-Token"
}
""")

# 2) Secure Storage
write_file("data/local/prefs/SecurePrefs.kt", """
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
        ZexLogger.e("SecurePrefs", "Failed to init EncryptedSharedPreferences. Falling back to standard.", e)
        context.getSharedPreferences(ZexConstants.FALLBACK_PREFS_NAME, Context.MODE_PRIVATE)
    }

    fun putString(key: String, value: String?) {
        prefs.edit().putString(key, value).apply()
    }

    fun getString(key: String, default: String? = null): String? {
        return prefs.getString(key, default)
    }

    fun putBoolean(key: String, value: Boolean) {
        prefs.edit().putBoolean(key, value).apply()
    }

    fun getBoolean(key: String, default: Boolean = false): Boolean {
        return prefs.getBoolean(key, default)
    }

    fun putInt(key: String, value: Int) {
        prefs.edit().putInt(key, value).apply()
    }

    fun getInt(key: String, default: Int = 0): Int {
        return prefs.getInt(key, default)
    }

    fun clear() {
        prefs.edit().clear().apply()
    }
}
""")

# 3) Network Layer - DI, API, Interceptor
write_file("di/NetworkModule.kt", """
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
            ZexLogger.d("OkHttp", message)
        }.apply {
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY else HttpLoggingInterceptor.Level.NONE
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

write_file("data/remote/api/ZexApi.kt", """
package com.zex.tracker.data.remote.api

import com.zex.tracker.data.remote.dto.AuthResponse
import com.zex.tracker.data.remote.dto.DeviceRegisterRequest
import com.zex.tracker.data.remote.dto.DeviceRegisterResponse
import com.zex.tracker.data.remote.dto.LoginRequest
import com.zex.tracker.data.remote.dto.RegisterRequest
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface ZexApi {
    @POST("auth/register")
    suspend fun registerOwner(@Body request: RegisterRequest): Response<AuthResponse>

    @POST("auth/login")
    suspend fun loginOwner(@Body request: LoginRequest): Response<AuthResponse>

    @GET("auth/me")
    suspend fun getOwnerMe(): Response<AuthResponse>

    @POST("devices/register")
    suspend fun registerDevice(@Body request: DeviceRegisterRequest): Response<DeviceRegisterResponse>
}
""")

write_file("data/remote/ApiResult.kt", """
package com.zex.tracker.data.remote

sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Error(val message: String, val code: Int? = null) : ApiResult<Nothing>()
}
""")

write_file("data/remote/dto/AuthDto.kt", """
package com.zex.tracker.data.remote.dto

data class RegisterRequest(
    val name: String,
    val email: String,
    val phone: String,
    val password: String,
    val password_confirmation: String,
    val pin_code: String
)

data class LoginRequest(
    val email: String,
    val password: String
)

data class AuthResponse(
    val owner: OwnerDto,
    val token: String? = null
)

data class OwnerDto(
    val id: Int,
    val name: String,
    val email: String,
    val phone: String?,
    val pin_code: String?
)
""")

write_file("data/remote/dto/DeviceDto.kt", """
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
    val id: Int,
    val device_uid: String,
    val name: String,
    val status: String
)
""")

# 3b) Repositories
write_file("data/repository/BaseRepository.kt", """
package com.zex.tracker.data.repository

import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.remote.ApiResult
import retrofit2.Response

abstract class BaseRepository {
    protected suspend fun <T> safeApiCall(apiCall: suspend () -> Response<T>): ApiResult<T> {
        return try {
            val response = apiCall()
            if (response.isSuccessful) {
                val body = response.body()
                if (body != null) {
                    ApiResult.Success(body)
                } else {
                    ApiResult.Error("Empty response body")
                }
            } else {
                val errorBody = response.errorBody()?.string()
                ZexLogger.w("BaseRepository", "API Error: ${response.code()} - $errorBody")
                val msg = parseError(response.code(), errorBody)
                ApiResult.Error(msg, response.code())
            }
        } catch (e: Exception) {
            ZexLogger.e("BaseRepository", "API Exception", e)
            ApiResult.Error(e.message ?: "Unknown error")
        }
    }

    private fun parseError(code: Int, errorBody: String?): String {
        return when (code) {
            401 -> "Unauthorized. Please login again."
            422 -> "Validation failed. Please check your inputs."
            500 -> "Server error. Please try again later."
            else -> "Error: $code. $errorBody"
        }
    }
}
""")

write_file("data/repository/AuthRepository.kt", """
package com.zex.tracker.data.repository

import com.zex.tracker.data.remote.ApiResult
import com.zex.tracker.data.remote.api.ZexApi
import com.zex.tracker.data.remote.dto.AuthResponse
import com.zex.tracker.data.remote.dto.LoginRequest
import com.zex.tracker.data.remote.dto.RegisterRequest
import javax.inject.Inject

class AuthRepository @Inject constructor(
    private val api: ZexApi
) : BaseRepository() {
    suspend fun register(request: RegisterRequest): ApiResult<AuthResponse> = safeApiCall {
        api.registerOwner(request)
    }

    suspend fun login(request: LoginRequest): ApiResult<AuthResponse> = safeApiCall {
        api.loginOwner(request)
    }
}
""")

write_file("data/repository/DeviceRepository.kt", """
package com.zex.tracker.data.repository

import com.zex.tracker.data.remote.ApiResult
import com.zex.tracker.data.remote.api.ZexApi
import com.zex.tracker.data.remote.dto.DeviceRegisterRequest
import com.zex.tracker.data.remote.dto.DeviceRegisterResponse
import javax.inject.Inject

class DeviceRepository @Inject constructor(
    private val api: ZexApi
) : BaseRepository() {
    suspend fun registerDevice(request: DeviceRegisterRequest): ApiResult<DeviceRegisterResponse> = safeApiCall {
        api.registerDevice(request)
    }
}
""")

# 4) Domain Models
write_file("domain/model/DomainModels.kt", """
package com.zex.tracker.domain.model

data class Owner(
    val id: Int,
    val name: String,
    val email: String,
    val phone: String?
)

data class Device(
    val id: Int,
    val deviceUid: String,
    val name: String,
    val status: String
)

data class Command(
    val id: Int,
    val type: String,
    val status: String
)

data class Alert(
    val id: Int,
    val type: String,
    val message: String
)

data class LocationPoint(
    val lat: Double,
    val lng: Double,
    val timestamp: Long
)
""")

# 6) Device Admin
write_file("receiver/ZexDeviceAdminReceiver.kt", """
package com.zex.tracker.receiver

import android.app.admin.DeviceAdminReceiver
import android.content.Context
import android.content.Intent
import com.zex.tracker.core.logging.ZexLogger

class ZexDeviceAdminReceiver : DeviceAdminReceiver() {
    override fun onEnabled(context: Context, intent: Intent) {
        super.onEnabled(context, intent)
        ZexLogger.i("DeviceAdmin", "Device Admin Enabled")
    }

    override fun onDisableRequested(context: Context, intent: Intent): CharSequence {
        ZexLogger.w("DeviceAdmin", "Device Admin Disable Requested")
        return "Disabling device admin will reduce anti-theft capabilities."
    }

    override fun onDisabled(context: Context, intent: Intent) {
        super.onDisabled(context, intent)
        ZexLogger.w("DeviceAdmin", "Device Admin Disabled")
    }
}
""")

write_res("xml/device_admin_policies.xml", """
<?xml version="1.0" encoding="utf-8"?>
<device-admin xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-policies>
        <force-lock />
        <wipe-data />
        <reset-password />
    </uses-policies>
</device-admin>
""")

# 8) UI Components
write_file("ui/components/UiComponents.kt", """
package com.zex.tracker.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties

@Composable
fun LoadingOverlay(isLoading: Boolean) {
    if (isLoading) {
        Dialog(
            onDismissRequest = {},
            properties = DialogProperties(dismissOnBackPress = false, dismissOnClickOutside = false)
        ) {
            Box(
                modifier = Modifier
                    .size(100.dp)
                    .background(Color.White, shape = MaterialTheme.shapes.medium),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator()
            }
        }
    }
}

@Composable
fun ErrorBanner(error: String?) {
    if (!error.isNullOrEmpty()) {
        Surface(
            color = MaterialTheme.colorScheme.errorContainer,
            modifier = Modifier.fillMaxWidth().padding(8.dp),
            shape = MaterialTheme.shapes.small
        ) {
            Text(
                text = error,
                color = MaterialTheme.colorScheme.onErrorContainer,
                modifier = Modifier.padding(16.dp),
                style = MaterialTheme.typography.bodyMedium
            )
        }
    }
}

@Composable
fun PrimaryButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true) {
    Button(
        onClick = onClick,
        modifier = modifier.fillMaxWidth().height(50.dp),
        enabled = enabled
    ) {
        Text(text, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun StatusDot(isHealthy: Boolean?) {
    val color = when (isHealthy) {
        true -> Color.Green
        false -> Color.Red
        null -> Color.Gray
    }
    Box(
        modifier = Modifier
            .size(12.dp)
            .background(color, CircleShape)
    )
}
""")

# Setup ViewModels
write_file("ui/screens/setup/SetupViewModel.kt", """
package com.zex.tracker.ui.screens.setup

import android.content.Context
import android.os.Build
import android.provider.Settings
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.zex.tracker.core.constants.ZexConstants
import com.zex.tracker.core.logging.ZexLogger
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.data.remote.ApiResult
import com.zex.tracker.data.remote.dto.DeviceRegisterRequest
import com.zex.tracker.data.remote.dto.LoginRequest
import com.zex.tracker.data.remote.dto.RegisterRequest
import com.zex.tracker.data.repository.AuthRepository
import com.zex.tracker.data.repository.DeviceRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.util.UUID
import javax.inject.Inject

@HiltViewModel
class SetupViewModel @Inject constructor(
    private val authRepo: AuthRepository,
    private val deviceRepo: DeviceRepository,
    private val prefs: SecurePrefs
) : ViewModel() {

    private val _uiState = MutableStateFlow(SetupUiState())
    val uiState: StateFlow<SetupUiState> = _uiState

    fun registerOwner(req: RegisterRequest, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val res = authRepo.register(req)) {
                is ApiResult.Success -> {
                    prefs.putString(ZexConstants.KEY_OWNER_TOKEN, res.data.token)
                    prefs.putInt(ZexConstants.KEY_OWNER_ID, res.data.owner.id)
                    ZexLogger.i("Setup", "Owner registered successfully")
                    _uiState.value = _uiState.value.copy(isLoading = false)
                    onSuccess()
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, error = res.message)
                }
            }
        }
    }

    fun loginOwner(req: LoginRequest, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            when (val res = authRepo.login(req)) {
                is ApiResult.Success -> {
                    prefs.putString(ZexConstants.KEY_OWNER_TOKEN, res.data.token)
                    prefs.putInt(ZexConstants.KEY_OWNER_ID, res.data.owner.id)
                    ZexLogger.i("Setup", "Owner logged in successfully")
                    _uiState.value = _uiState.value.copy(isLoading = false)
                    onSuccess()
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, error = res.message)
                }
            }
        }
    }

    fun registerDevice(context: Context, deviceName: String, onSuccess: () -> Unit) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            var uid = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
            if (uid.isNullOrEmpty()) {
                uid = UUID.randomUUID().toString()
            }
            val finalUid = "zex-uid-$uid"
            
            val req = DeviceRegisterRequest(
                device_uid = finalUid,
                device_name = deviceName,
                device_model = Build.MODEL,
                android_version = Build.VERSION.RELEASE,
                sim_iccid = null // handled later
            )

            when (val res = deviceRepo.registerDevice(req)) {
                is ApiResult.Success -> {
                    prefs.putString(ZexConstants.KEY_DEVICE_TOKEN, res.data.device_token)
                    prefs.putString(ZexConstants.KEY_DEVICE_UID, finalUid)
                    ZexLogger.i("Setup", "Device registered successfully")
                    _uiState.value = _uiState.value.copy(isLoading = false)
                    onSuccess()
                }
                is ApiResult.Error -> {
                    _uiState.value = _uiState.value.copy(isLoading = false, error = res.message)
                }
            }
        }
    }

    fun completeSetup() {
        prefs.putBoolean(ZexConstants.KEY_IS_SETUP_COMPLETE, true)
    }
}

data class SetupUiState(
    val isLoading: Boolean = false,
    val error: String? = null
)
""")

# Add Navigation and basic screen placeholders
write_file("ui/Navigation.kt", """
package com.zex.tracker.ui

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.zex.tracker.ui.screens.setup.WelcomeScreen
import com.zex.tracker.ui.screens.setup.AuthScreen
import com.zex.tracker.ui.screens.setup.DeviceRegisterScreen
import com.zex.tracker.ui.screens.setup.PermissionsScreen
import com.zex.tracker.ui.screens.setup.DeviceAdminScreen
import com.zex.tracker.ui.screens.dashboard.DashboardScreen
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.core.constants.ZexConstants

@Composable
fun ZexNavHost(prefs: SecurePrefs) {
    val navController = rememberNavController()
    val isSetup = prefs.getBoolean(ZexConstants.KEY_IS_SETUP_COMPLETE)
    val startDest = if (isSetup) "dashboard" else "welcome"

    NavHost(navController = navController, startDestination = startDest) {
        composable("welcome") { WelcomeScreen(navController) }
        composable("auth") { AuthScreen(navController) }
        composable("device_register") { DeviceRegisterScreen(navController) }
        composable("permissions") { PermissionsScreen(navController) }
        composable("device_admin") { DeviceAdminScreen(navController, onFinish = {
            prefs.putBoolean(ZexConstants.KEY_IS_SETUP_COMPLETE, true)
            navController.navigate("dashboard") {
                popUpTo(0)
            }
        }) }
        composable("dashboard") { DashboardScreen(prefs) }
    }
}
""")

write_file("ui/screens/setup/Screens.kt", """
package com.zex.tracker.ui.screens.setup

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavController
import com.zex.tracker.ui.components.PrimaryButton
import com.zex.tracker.ui.components.LoadingOverlay
import com.zex.tracker.ui.components.ErrorBanner
import com.zex.tracker.data.remote.dto.RegisterRequest
import com.zex.tracker.data.remote.dto.LoginRequest

@Composable
fun WelcomeScreen(navController: NavController) {
    Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("Welcome to ZEX Tracker", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(32.dp))
        PrimaryButton("Continue", onClick = { navController.navigate("auth") })
    }
}

@Composable
fun AuthScreen(navController: NavController, viewModel: SetupViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    var isLogin by remember { mutableStateOf(false) }
    
    // Simple state
    var email by remember { mutableStateOf("") }
    var pass by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var pin by remember { mutableStateOf("") }

    LoadingOverlay(state.isLoading)

    Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text(if (isLogin) "Login" else "Register", style = MaterialTheme.typography.headlineMedium)
        ErrorBanner(state.error)
        
        OutlinedTextField(value = email, onValueChange = { email = it }, label = { Text("Email") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(value = pass, onValueChange = { pass = it }, label = { Text("Password") }, modifier = Modifier.fillMaxWidth())
        
        if (!isLogin) {
            OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Name") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(value = phone, onValueChange = { phone = it }, label = { Text("Phone") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(value = pin, onValueChange = { pin = it }, label = { Text("6-digit PIN") }, modifier = Modifier.fillMaxWidth())
        }
        
        Spacer(Modifier.height(16.dp))
        PrimaryButton("Submit", onClick = {
            if (isLogin) {
                viewModel.loginOwner(LoginRequest(email, pass)) { navController.navigate("device_register") }
            } else {
                viewModel.registerOwner(RegisterRequest(name, email, phone, pass, pass, pin)) { navController.navigate("device_register") }
            }
        })
        TextButton(onClick = { isLogin = !isLogin }) { Text("Toggle Login/Register") }
    }
}

@Composable
fun DeviceRegisterScreen(navController: NavController, viewModel: SetupViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    var deviceName by remember { mutableStateOf("My Phone") }
    val context = LocalContext.current

    LoadingOverlay(state.isLoading)

    Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("Register Device", style = MaterialTheme.typography.headlineMedium)
        ErrorBanner(state.error)
        OutlinedTextField(value = deviceName, onValueChange = { deviceName = it }, label = { Text("Device Name") }, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(16.dp))
        PrimaryButton("Register", onClick = {
            viewModel.registerDevice(context, deviceName) { navController.navigate("permissions") }
        })
    }
}

@Composable
fun PermissionsScreen(navController: NavController) {
    Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("Permissions", style = MaterialTheme.typography.headlineMedium)
        Text("Please grant necessary permissions (Location, SMS, etc).")
        Spacer(Modifier.height(32.dp))
        PrimaryButton("Grant & Continue", onClick = { navController.navigate("device_admin") })
    }
}

@Composable
fun DeviceAdminScreen(navController: NavController, onFinish: () -> Unit) {
    Column(modifier = Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
        Text("Device Admin", style = MaterialTheme.typography.headlineMedium)
        Text("Enable Device Admin for wipe/lock features.")
        Spacer(Modifier.height(32.dp))
        PrimaryButton("Enable", onClick = onFinish)
        TextButton(onClick = onFinish) { Text("Skip for now") }
    }
}
""")

write_file("ui/screens/dashboard/DashboardScreen.kt", """
package com.zex.tracker.ui.screens.dashboard

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.zex.tracker.data.local.prefs.SecurePrefs
import com.zex.tracker.core.constants.ZexConstants

@Composable
fun DashboardScreen(prefs: SecurePrefs) {
    val uid = prefs.getString(ZexConstants.KEY_DEVICE_UID) ?: "Unknown UID"
    
    Column(modifier = Modifier.fillMaxSize().padding(24.dp)) {
        Text("Dashboard", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(16.dp))
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Device UID: $uid")
                Text("Status: ACTIVE")
            }
        }
    }
}
""")
