import 'package:flutter/material.dart';
import 'theme/app_theme.dart';
import 'screens/app_shell.dart';

void main() {
  runApp(const SmartCropApp());
}

class SmartCropApp extends StatelessWidget {
  const SmartCropApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Crop Advisory',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: const AppShell(),
    );
  }
}