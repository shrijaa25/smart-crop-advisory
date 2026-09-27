import 'package:flutter/material.dart';
import '../widgets/app_sidebar.dart';
import '../widgets/app_topbar.dart';
import 'home_screen.dart';
import 'my_crops_screen.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _index = 0;

  static const _titles = [
    'Home',
    'My Crops',
    'Advisory',
    'Scan',
    'History',
    'Alerts',
    'Profile',
  ];

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.of(context).size.width;
    final collapsed = width < 1100;

    return Scaffold(
      body: Row(
        children: [
          AppSidebar(
            selectedIndex: _index,
            onSelect: (i) => setState(() => _index = i),
            collapsed: collapsed,
          ),
          Expanded(
            child: Column(
              children: [
                AppTopbar(title: _titles[_index], farmerName: 'Shrijaa'),
                Expanded(
                  child: IndexedStack(
                    index: _index,
                    children: const [
                      HomeScreen(),
                      MyCropsScreen(),
                      _Placeholder(label: 'Advisory'),
                      _Placeholder(label: 'Scan'),
                      _Placeholder(label: 'History'),
                      _Placeholder(label: 'Alerts'),
                      _Placeholder(label: 'Profile'),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Placeholder extends StatelessWidget {
  final String label;
  const _Placeholder({required this.label});

  @override
  Widget build(BuildContext context) {
    return Center(child: Text('$label — coming soon'));
  }
}