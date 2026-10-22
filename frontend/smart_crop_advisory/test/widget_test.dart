import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:smart_crop_advisory/screens/login_screen.dart';
import 'package:smart_crop_advisory/services/auth_controller.dart';

void main() {
  testWidgets(
    'login screen renders labeled credentials and registration action',
    (tester) async {
      final auth = AuthController();
      await tester.pumpWidget(MaterialApp(home: LoginScreen(auth: auth)));

      expect(find.text('Welcome back'), findsOneWidget);
      expect(find.text('Phone number'), findsOneWidget);
      expect(find.text('Password'), findsOneWidget);
      expect(find.text('Sign in'), findsOneWidget);
      expect(find.text('Create account'), findsOneWidget);

      auth.dispose();
    },
  );
}
