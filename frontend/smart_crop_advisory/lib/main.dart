import 'package:flutter/material.dart';
import 'theme/app_theme.dart';
import 'screens/auth_gate.dart';
import 'services/auth_controller.dart';

void main() {
  runApp(const SmartCropApp());
}

class SmartCropApp extends StatefulWidget {
  const SmartCropApp({super.key});

  @override
  State<SmartCropApp> createState() => _SmartCropAppState();
}

class _SmartCropAppState extends State<SmartCropApp> {
  late final AuthController _auth;

  @override
  void initState() {
    super.initState();
    _auth = AuthController();
    _auth.restoreSession();
  }

  @override
  void dispose() {
    _auth.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Crop Advisory',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: AuthGate(auth: _auth),
    );
  }
}
