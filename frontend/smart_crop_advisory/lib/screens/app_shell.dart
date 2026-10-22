import 'package:flutter/material.dart';

import '../services/auth_controller.dart';
import '../theme/app_colors.dart';
import 'advisory_screen.dart';
import 'alerts_screen.dart';
import 'daily_tasks_screen.dart';
import 'history_screen.dart';
import 'profile_screen.dart';
import 'scan_screen.dart';

class AppShell extends StatefulWidget {
  final AuthController auth;
  const AppShell({super.key, required this.auth});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _index = 0;

  static const _destinations = [
    (label: 'Advisory', icon: Icons.eco_outlined, selected: Icons.eco),
    (
      label: 'Scan',
      icon: Icons.document_scanner_outlined,
      selected: Icons.document_scanner,
    ),
    (
      label: 'Daily Tasks',
      icon: Icons.calendar_today_outlined,
      selected: Icons.calendar_today,
    ),
    (label: 'History', icon: Icons.history_outlined, selected: Icons.history),
    (
      label: 'Alerts',
      icon: Icons.notifications_none,
      selected: Icons.notifications_active,
    ),
    (label: 'Profile', icon: Icons.person_outline, selected: Icons.person),
  ];

  @override
  Widget build(BuildContext context) {
    final pages = [
      AdvisoryScreen(auth: widget.auth),
      ScanScreen(auth: widget.auth),
      DailyTasksScreen(auth: widget.auth),
      HistoryScreen(auth: widget.auth),
      AlertsScreen(auth: widget.auth),
      ProfileScreen(auth: widget.auth),
    ];

    return PopScope(
      canPop: _index == 0,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop && _index != 0) setState(() => _index = 0);
      },
      child: Scaffold(
        body: SafeArea(
          bottom: false,
          child: IndexedStack(index: _index, children: pages),
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (index) => setState(() => _index = index),
          backgroundColor: AppColors.surface,
          indicatorColor: AppColors.primaryLight,
          destinations: [
            for (var i = 0; i < _destinations.length; i++)
              NavigationDestination(
                icon: Icon(_destinations[i].icon),
                selectedIcon: Icon(_destinations[i].selected),
                label: _destinations[i].label,
              ),
          ],
        ),
      ),
    );
  }
}
