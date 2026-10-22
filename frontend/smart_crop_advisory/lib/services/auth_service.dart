import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../models/daily_task.dart';
import '../models/crop_cycle.dart';
import '../models/farm.dart';
import '../models/farmer_profile.dart';
import 'api_client.dart';

class AuthService {
  static const _tokenKey = 'smart_crop_access_token';

  final ApiClient api;
  final FlutterSecureStorage storage;

  const AuthService({required this.api, required this.storage});

  Future<FarmerProfile> register({
    required String fullName,
    required String phone,
    required String password,
    required String preferredLanguage,
  }) async {
    final json = await api.postJson('auth/register', {
      'full_name': fullName,
      'phone': phone,
      'password': password,
      'preferred_language': preferredLanguage,
    });
    return FarmerProfile.fromJson(json);
  }

  Future<Map<String, dynamic>> login({
    required String phone,
    required String password,
  }) {
    return api.postForm('auth/login', {
      'username': phone,
      'password': password,
    });
  }

  Future<FarmerProfile> me(String token) async {
    return FarmerProfile.fromJson(await api.getObject('auth/me', token: token));
  }

  Future<List<DailyTask>> tasks(String token, DateTime day) async {
    final rows = await api.getList(
      'tasks?task_date=${_dateString(day)}',
      token: token,
    );
    return rows
        .whereType<Map<String, dynamic>>()
        .map(DailyTask.fromJson)
        .toList();
  }

  Future<List<DailyTask>> taskHistory(String token) async => (await api.getList(
    'tasks',
    token: token,
  )).whereType<Map<String, dynamic>>().map(DailyTask.fromJson).toList();

  Future<List<Map<String, dynamic>>> observations(String token) async {
    final rows = await api.getList(
      'tasks/observations',
      token: token,
    );

    return rows
        .whereType<Map<String, dynamic>>()
        .map((row) => Map<String, dynamic>.from(row))
        .toList();
  }

  Future<List<DailyTask>> upcomingTasks(String token) async =>
      (await api.getList(
        'tasks/upcoming',
        token: token,
      )).whereType<Map<String, dynamic>>().map(DailyTask.fromJson).toList();

  Future<Map<String, dynamic>> diseaseDetectionStatus(String token) =>
      api.getObject('tasks/disease-detection/status', token: token);

  Future<Map<String, dynamic>> weather(String town) =>
      api.getObject(
        'weather?town=${Uri.encodeQueryComponent(town)}',
      );

  Future<List<Farm>> farms(String token) async => (await api.getList(
    'farms',
    token: token,
  )).whereType<Map<String, dynamic>>().map(Farm.fromJson).toList();

  Future<Farm> createFarm(String token, Map<String, dynamic> farm) async =>
      Farm.fromJson(await api.postJson('farms', farm, token: token));

  Future<List<CropCycle>> cropCycles(String token) async => (await api.getList(
    'crop-cycles',
    token: token,
  )).whereType<Map<String, dynamic>>().map(CropCycle.fromJson).toList();

  Future<CropCycle> createCropCycle(
    String token,
    int farmId,
    Map<String, dynamic> crop,
  ) async => CropCycle.fromJson(
    await api.postJson('farms/$farmId/crops', crop, token: token),
  );

  Future<Map<String, dynamic>> cropStage(
    String token,
    int cropCycleId,
    DateTime day,
  ) => api.getObject(
    'tasks/crop-stage?crop_cycle_id=$cropCycleId&target_date=${_dateString(day)}',
    token: token,
  );

  Future<Map<String, dynamic>> weatherRisk(
    String token,
    int cropCycleId,
    DateTime day,
  ) =>
      api.getObject(
        'tasks/weather-risk/$cropCycleId?target_date=${_dateString(day)}',
        token: token,
      );

  Future<Map<String, dynamic>> saveObservation(
    String token, {
    required int cropCycleId,
    int? taskId,
    required String note,
  }) {
    return api.postJson(
      'tasks/observations',
      {
        'crop_cycle_id': cropCycleId,
        'task_id': ?taskId,
        'note': note,
        'photo_reference': null,
      },
      token: token,
    );
  }

  Future<Map<String, dynamic>> generateTasks(String token, DateTime day) =>
      api.postJson(
        'tasks/generate?target_date=${_dateString(day)}',
        const {},
        token: token,
      );

  Future<DailyTask> completeTask(String token, int taskId) async =>
      DailyTask.fromJson(
        await api.patchJson('tasks/$taskId/complete', const {}, token: token),
      );

  Future<DailyTask> reopenTask(String token, int taskId) async =>
      DailyTask.fromJson(
        await api.patchJson('tasks/$taskId/reopen', const {}, token: token),
      );

  String _dateString(DateTime day) =>
      '${day.year.toString().padLeft(4, '0')}-'
      '${day.month.toString().padLeft(2, '0')}-'
      '${day.day.toString().padLeft(2, '0')}';

  Future<String?> readToken() => storage.read(key: _tokenKey);

  Future<void> saveToken(String token) =>
      storage.write(key: _tokenKey, value: token);

  Future<void> clearToken() => storage.delete(key: _tokenKey);
}
