

Await Science
=================================

.. tabs::
    .. code-tab:: mast
        
        await scan():
            scan tab "scan":
                scan results "Scan"
            scan tab "bio":
                scan results "Bio"
        end_await
        
        

    .. code-tab:: py PyMast
        
              self.await_science({
                "scan": self.scan_default,
                "bio": self.scan_bio,
                "intel": self.scan_intel,
                "signl": self.scan_signl
            })


        def scan_default(self, event):
            return "This space object is now scanned, in the most general way. This text was generated by the script."
        
        def scan_intel(self, event):
            return "This space object is detailed in the ship's computer banks. This text was generated by the script."
        
        def scan_bio(self, event):
            return "This space object has indeterminate life signs. This text was generated by the script."
        def scan_signl(self, event):
            return "This space object radiating signals. This text was generated by the script."

        



