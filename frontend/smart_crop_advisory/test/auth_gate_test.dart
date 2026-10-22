import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_crop_advisory/models/crop_cycle.dart';
import 'package:smart_crop_advisory/models/daily_task.dart';
import 'package:smart_crop_advisory/models/farm.dart';
import 'package:smart_crop_advisory/screens/auth_gate.dart';
import 'package:smart_crop_advisory/screens/crop_registration_screen.dart';
import 'package:smart_crop_advisory/services/api_client.dart';
import 'package:smart_crop_advisory/services/auth_controller.dart';

void main() {
  testWidgets('empty crop-cycle response requires onboarding', (tester) async {
    final auth = _GateTestAuth(cycles: const []);
    await tester.pumpWidget(MaterialApp(home: AuthGate(auth: auth)));
    await tester.pumpAndSettle();

    expect(find.text('Farm setup'), findsOneWidget);
    expect(find.text('Get started'), findsOneWidget);
    expect(find.text('Advisory'), findsNothing);
    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();
    expect(find.text('Farm setup'), findsOneWidget);
    auth.dispose();
  });

  testWidgets('existing crop cycles allow dashboard access', (tester) async {
    final auth = _GateTestAuth(cycles: [_cycle(1), _cycle(2)]);
    await tester.pumpWidget(MaterialApp(home: AuthGate(auth: auth)));
    await tester.pumpAndSettle();

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.text('Advisory'), findsOneWidget);
    auth.dispose();
  });

  testWidgets('crop-cycle lookup failure stays gated and offers retry', (
    tester,
  ) async {
    final auth = _GateTestAuth(cycles: const [], failCycleLookup: true);
    await tester.pumpWidget(MaterialApp(home: AuthGate(auth: auth)));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('Unable to check your crop setup'),
      findsOneWidget,
    );
    expect(find.text('Retry'), findsOneWidget);
    expect(find.byType(NavigationBar), findsNothing);
    auth.failCycleLookup = false;
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(find.text('Farm setup'), findsOneWidget);
    auth.dispose();
  });

  testWidgets('logging out during onboarding returns to login', (tester) async {
    final auth = _GateTestAuth(cycles: const []);
    await tester.pumpWidget(MaterialApp(home: AuthGate(auth: auth)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Log out'));
    await tester.pumpAndSettle();

    expect(find.text('Welcome back'), findsOneWidget);
    auth.dispose();
  });

  testWidgets('crop form rejects missing date and non-positive area', (
    tester,
  ) async {
    final auth = _GateTestAuth(cycles: const [], farms: [_farm()]);
    await tester.pumpWidget(
      MaterialApp(home: CropRegistrationScreen(auth: auth)),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Save Crop & Continue'));
    await tester.pumpAndSettle();
    expect(find.text('Enter an area above zero.'), findsOneWidget);
    expect(find.text('Select a transplanting date.'), findsOneWidget);
    auth.dispose();
  });
}

CropCycle _cycle(int id) => CropCycle(
  id: id,
  farmId: 1,
  cropName: 'tomato',
  variety: null,
  plantingDate: DateTime(2026, 1, 1),
  plantingMethod: 'transplanting',
  areaValue: 1,
  areaUnit: 'acre',
  status: 'active',
  notes: null,
);

Farm _farm() => const Farm(
  id: 1,
  name: 'Test farm',
  village: null,
  district: null,
  state: null,
  latitude: null,
  longitude: null,
  areaValue: null,
  areaUnit: 'acre',
  soilType: null,
  irrigationMethod: null,
);

class _GateTestAuth extends AuthController {
  final List<CropCycle> cycles;
  final List<Farm> farms;
  bool failCycleLookup;
  AuthStatus _testStatus = AuthStatus.signedIn;

  _GateTestAuth({
    required this.cycles,
    this.farms = const [],
    this.failCycleLookup = false,
  });

  @override
  AuthStatus get status => _testStatus;

  @override
  Future<void> logout() async {
    _testStatus = AuthStatus.signedOut;
    notifyListeners();
  }

  @override
  Future<List<CropCycle>> loadCropCycles() async {
    if (failCycleLookup) throw const ApiException('Service unavailable.');
    return cycles;
  }

  @override
  Future<List<Farm>> loadFarms() async => farms;

  @override
  Future<List<DailyTask>> loadTasksForToday() async => const [];

  @override
  Future<List<DailyTask>> loadTaskHistory() async => const [];

  @override
  Future<Map<String, dynamic>> generateTasks(DateTime day) async => const {};
}
