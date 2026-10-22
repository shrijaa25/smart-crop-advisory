import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:image_picker/image_picker.dart';

import '../models/daily_task.dart';
import '../models/crop_cycle.dart';
import '../models/farm.dart';
import '../models/farmer_profile.dart';
import 'api_client.dart';
import 'auth_service.dart';

enum AuthStatus { checking, signedOut, signedIn }

class AuthController extends ChangeNotifier {
  AuthController({FlutterSecureStorage? storage}) {
    final secureStorage = storage ?? const FlutterSecureStorage();
    _api = ApiClient(onUnauthorized: _onUnauthorized);
    _service = AuthService(api: _api, storage: secureStorage);
  }

  late final ApiClient _api;
  late final AuthService _service;
  AuthStatus _status = AuthStatus.signedOut;
  FarmerProfile? _profile;
  String? _token;
  String? _startupMessage;

  AuthStatus get status => _status;
  FarmerProfile? get profile => _profile;
  String? get startupMessage => _startupMessage;

  Future<void> restoreSession() async {
    _status = AuthStatus.checking;
    _startupMessage = null;
    notifyListeners();
    try {
      final savedToken = await _service.readToken();
      if (savedToken == null || savedToken.isEmpty) {
        _status = AuthStatus.signedOut;
        notifyListeners();
        return;
      }
      _token = savedToken;
      _profile = await _service.me(savedToken);
      _status = AuthStatus.signedIn;
    } on ApiException catch (error) {
      _profile = null;
      _token = null;
      _status = AuthStatus.signedOut;
      if (error.statusCode != 401) {
        _startupMessage =
            'Could not verify your saved session. Please sign in.';
      }
    } catch (_) {
      _profile = null;
      _token = null;
      _status = AuthStatus.signedOut;
      _startupMessage =
          'Could not connect to the service. Please sign in again.';
    }
    notifyListeners();
  }

  Future<FarmerProfile> register({
    required String fullName,
    required String phone,
    required String password,
    required String preferredLanguage,
  }) {
    return _service.register(
      fullName: fullName,
      phone: phone,
      password: password,
      preferredLanguage: preferredLanguage,
    );
  }

  Future<void> login({required String phone, required String password}) async {
    final tokenResponse = await _service.login(
      phone: phone,
      password: password,
    );
    final newToken = tokenResponse['access_token'];
    if (newToken is! String || newToken.isEmpty) {
      throw const ApiException('The server did not return an access token.');
    }

    await _service.saveToken(newToken);
    _token = newToken;
    try {
      _profile = await _service.me(newToken);
    } catch (_) {
      await _service.clearToken();
      _token = null;
      _profile = null;
      rethrow;
    }
    _startupMessage = null;
    _status = AuthStatus.signedIn;
    notifyListeners();
  }

  Future<List<DailyTask>> loadTasksForToday() {
    return loadTasks(DateTime.now());
  }

  Future<List<DailyTask>> loadTasks(DateTime day) {
    return _service.tasks(_requiredToken(), day);
  }

  Future<List<DailyTask>> loadTaskHistory() =>
      _service.taskHistory(_requiredToken());

  Future<List<Map<String, dynamic>>> loadObservations() =>
      _service.observations(_requiredToken());

  Future<List<DailyTask>> loadUpcomingTasks() =>
      _service.upcomingTasks(_requiredToken());

  Future<Map<String, dynamic>> loadDiseaseDetectionStatus() =>
      _service.diseaseDetectionStatus(_requiredToken());

  Future<Map<String, dynamic>> predictDisease(XFile image) async =>
      _api.postMultipartFile(
        'disease/predict',
        fileName: image.name,
        bytes: await image.readAsBytes(),
      );

  Future<Map<String, dynamic>> loadWeather(String town) async {
    final response = await _service.weather(town);

    // The backend returns weather inside the "weather" field.
    final weatherData = response['weather'];

    if (weatherData is! Map) {
      throw const ApiException('Invalid weather data received from server.');
    }

    return {
      ...Map<String, dynamic>.from(weatherData),
      'town': response['town'] ?? town,
      'state': response['state'],
    };
  }

  Future<List<Farm>> loadFarms() => _service.farms(_requiredToken());

  Future<Farm> createFarm(Map<String, dynamic> farm) =>
      _service.createFarm(_requiredToken(), farm);

  Future<List<CropCycle>> loadCropCycles() =>
      _service.cropCycles(_requiredToken());

  Future<CropCycle> createCropCycle(int farmId, Map<String, dynamic> crop) =>
      _service.createCropCycle(_requiredToken(), farmId, crop);

  Future<Map<String, dynamic>> loadCropStage(int cropCycleId, DateTime day) =>
      _service.cropStage(_requiredToken(), cropCycleId, day);

  Future<Map<String, dynamic>> loadWeatherRisk(int cropCycleId, DateTime day) =>
      _service.weatherRisk(_requiredToken(), cropCycleId, day);

  Future<Map<String, dynamic>> loadDiseaseTreatment({
    required String crop,
    required String disease,
  }) => _api.postJson('tasks/disease-treatment', {
    'crop': crop,
    'disease': disease,
  }, token: _requiredToken());

  Future<Map<String, dynamic>> saveObservation({
    required int cropCycleId,
    int? taskId,
    required String note,
  }) {
    return _service.saveObservation(
      _requiredToken(),
      cropCycleId: cropCycleId,
      taskId: taskId,
      note: note,
    );
  }

  Future<Map<String, dynamic>> generateTasks(DateTime day) =>
      _service.generateTasks(_requiredToken(), day);

  Future<DailyTask> completeTask(int taskId) =>
      _service.completeTask(_requiredToken(), taskId);

  Future<DailyTask> reopenTask(int taskId) =>
      _service.reopenTask(_requiredToken(), taskId);

  String _requiredToken() {
    final token = _token;
    if (token == null) {
      throw const ApiException('Please sign in again.', statusCode: 401);
    }
    return token;
  }

  Future<void> logout() async {
    await _service.clearToken();
    _token = null;
    _profile = null;
    _startupMessage = null;
    _status = AuthStatus.signedOut;
    notifyListeners();
  }

  Future<void> _onUnauthorized() async {
    await _service.clearToken();
    _token = null;
    _profile = null;
    _status = AuthStatus.signedOut;
    _startupMessage = 'Your session expired. Please sign in again.';
    notifyListeners();
  }
}
